"""Periodic service expiry, traffic warnings, and Xenet balance monitoring."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

CHECK_HOURS = [8, 12, 16]  # 8am, 12pm, 4pm
XENET_BALANCE_WARNING_THRESHOLD = 100  # Warn when balance is below this amount


async def _check_panel_traffic(bot):
    """Check panel traffic usage and notify admins if > 60%."""
    from .config import ADMIN_IDS
    from .panel_client import PanelAPIError, panel_client

    try:
        admin_stats = await panel_client.get_admin_stats()
        total_traffic = admin_stats.get("data_limit", 0)
        if not total_traffic:
            return

        # Get used traffic from system stats
        system_stats = await panel_client.get_system_stats()
        incoming = system_stats.get("incoming_bandwidth", 0)
        outgoing = system_stats.get("outgoing_bandwidth", 0)
        used_traffic = incoming + outgoing

        if total_traffic > 0:
            usage_percent = (used_traffic / total_traffic) * 100
            if usage_percent >= 60:
                used_gb = used_traffic / (1024**3)
                total_gb = total_traffic / (1024**3)
                remaining_gb = total_gb - used_gb
                text = (
                    f"⚠️ هشدار: ترافیک پنل در حال اتمام است!\n\n"
                    f"📤 ترافیک مصرف‌شده: {used_gb:.1f} گیگ\n"
                    f"💾 ترافیک کل: {total_gb:.1f} گیگ\n"
                    f"📊 درصد مصرف: {usage_percent:.1f}%\n"
                    f"📦 ترافیک باقی‌مانده: {remaining_gb:.1f} گیگ"
                )
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, text)
                    except Exception:
                        logger.warning("Failed to send panel traffic warning to admin %s", admin_id)
    except PanelAPIError:
        logger.exception("Failed to check panel traffic")


async def _check_xenet_balance(bot):
    """Check Xenet balance and notify admins if low."""
    from .config import ADMIN_IDS, XENET_API_KEY
    from .xenet_client import XenetAPIError, xenet_client

    if not XENET_API_KEY:
        return  # Skip if Xenet is not configured

    try:
        reseller = await xenet_client.get_balance()
        balance = reseller.get("balance", 0)
        if balance < XENET_BALANCE_WARNING_THRESHOLD:
            text = (
                f"⚠️ هشدار: موجودی Xenet رو به اتمام است!\n\n"
                f"💰 موجودی فعلی: {balance:,} تومان\n"
                f"📊 حداقل مورد نیاز: {XENET_BALANCE_WARNING_THRESHOLD:,} تومان\n\n"
                f"لطفاً موجودی حساب Xenet خود را شارژ کنید."
            )
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, text)
                except Exception:
                    logger.warning("Failed to send Xenet balance warning to admin %s", admin_id)
    except XenetAPIError:
        logger.exception("Failed to check Xenet balance")


async def _check_services(bot):
    """Check all active services and send warnings."""
    from .db import async_session
    from .models import Service
    from .panel_client import PanelAPIError, panel_client
    from .services_repo import update_service
    from sqlalchemy import select

    now = datetime.now(timezone.utc)

    async with async_session() as session:
        result = await session.execute(
            select(Service).where(Service.status == "active")
        )
        services = result.scalars().all()

    for service in services:
        try:
            await _check_single_service(bot, service, now)
        except Exception:
            logger.exception("Error checking service %s", service.id)


async def _check_single_service(bot, service, now: datetime):
    """Check a single service and send warning/expired if needed.

    Deduplication: each notification type (warning or expired) is sent at most
    once per service period.  "Once per period" means we track the timestamp of
    the last sent notification and only re-send if the service was renewed
    (expires_at moved forward) since the last notification.
    """
    from .panel_client import PanelAPIError, panel_client
    from .settings_repo import get_setting
    from .xenet_client import XenetAPIError, xenet_client
    from .services_repo import update_service

    # --- Read admin notification settings ---
    settings_time_warning = (await get_setting("notify_time_warning")) == "1"
    settings_time_expired = (await get_setting("notify_time_expired")) == "1"
    settings_traffic_warning = (await get_setting("notify_traffic_warning")) == "1"
    settings_traffic_expired = (await get_setting("notify_traffic_expired")) == "1"

    # --- Determine current warning / expired flags ---
    time_warning = False
    time_expired = False
    if service.expires_at:
        expires = service.expires_at if service.expires_at.tzinfo else service.expires_at.replace(tzinfo=timezone.utc)
        created = service.created_at.replace(tzinfo=timezone.utc) if service.created_at.tzinfo is None else service.created_at
        if expires <= now:
            time_expired = True
        else:
            remaining = (expires - now).total_seconds()
            total = (expires - created).total_seconds()
            if total > 0 and remaining / total <= 0.1:
                time_warning = True

    traffic_warning = False
    traffic_expired = False
    if service.service_type != "unlimited":
        try:
            panel_user = await panel_client.get_user(service.panel_username)
            bytes_used = (panel_user.raw.get("usage")
                          or panel_user.raw.get("data_usage")
                          or panel_user.raw.get("used_traffic") or 0)
            total_bytes = float(service.traffic_gb) * 1024 ** 3
            if total_bytes > 0:
                usage_ratio = bytes_used / total_bytes
                if usage_ratio >= 1.0:
                    traffic_expired = True
                elif usage_ratio >= 0.9:
                    traffic_warning = True
        except PanelAPIError:
            pass
    else:
        if service.xenet_account_id:
            try:
                xenet_config = await xenet_client.get_v2_account(service.xenet_account_id)
                days_left = xenet_config.get("days_left", 30)
                if days_left <= 0:
                    time_expired = True
                elif days_left <= 3:
                    time_warning = True
            except XenetAPIError:
                pass

    # --- Apply admin settings: filter by enabled notification types ---
    if time_warning and not settings_time_warning:
        time_warning = False
    if time_expired and not settings_time_expired:
        time_expired = False
    if traffic_warning and not settings_traffic_warning:
        traffic_warning = False
    if traffic_expired and not settings_traffic_expired:
        traffic_expired = False

    wants_expired = time_expired or traffic_expired
    wants_warning = time_warning or traffic_warning

    # --- Deduplication ---
    # A warning is only re-sent when expires_at has moved forward since the
    # last warning (i.e. the service was renewed).  An expired notification is
    # only re-sent when the service was previously renewed *after* the last
    # expired notification and has expired again.
    should_send_expired = False
    should_send_warning = False

    if wants_expired:
        last = service.last_expired_sent_at
        if last is None or (service.expires_at and service.expires_at > last):
            should_send_expired = True
    elif wants_warning:
        last = service.last_warning_sent_at
        if last is None or (service.expires_at and service.expires_at > last):
            should_send_warning = True

    if not should_send_expired and not should_send_warning:
        return

    # --- Send and record ---
    if should_send_expired:
        await _send_expired_message(bot, service, time_expired, traffic_expired)
        await update_service(service.id, last_expired_sent_at=now)
    elif should_send_warning:
        await _send_warning_message(bot, service, time_warning, traffic_warning)
        await update_service(service.id, last_warning_sent_at=now)


async def _send_warning_message(bot, service, time_warning: bool, traffic_warning: bool):
    """Send warning message to user."""
    lines = ["⚠️ هشدار: سرویس شما در حال اتمام است!\n"]

    if time_warning:
        if service.service_type == "unlimited" and service.xenet_account_id:
            # For unlimited services, show Xenet days left
            try:
                from .xenet_client import xenet_client
                xenet_config = await xenet_client.get_v2_account(service.xenet_account_id)
                days_left = xenet_config.get("days_left", 0)
                lines.append(f"📅 زمان باقی‌مانده: {days_left} روز")
            except Exception:
                lines.append("📅 زمان باقی‌مانده: کمتر از ۳ روز")
        else:
            expires = service.expires_at if service.expires_at.tzinfo else service.expires_at.replace(tzinfo=timezone.utc)
            remaining_days = (expires - datetime.now(timezone.utc)).days
            lines.append(f"📅 زمان باقی‌مانده: {remaining_days} روز")

    if traffic_warning:
        try:
            from .panel_client import panel_client
            panel_user = await panel_client.get_user(service.panel_username)
            bytes_used = panel_user.raw.get("usage") or panel_user.raw.get("data_usage") or panel_user.raw.get("used_traffic") or 0
            used_gb = bytes_used / (1024**3)
            lines.append(f"🌐 ترافیک مصرف‌شده: {used_gb:.1f} از {service.traffic_gb} گیگ")
        except Exception:
            pass

    lines.append("\nبرای تمدید سرویس، از منوی مدیریت سرویس استفاده کنید.")

    try:
        await bot.send_message(service.owner_telegram_id, "\n".join(lines))
    except Exception:
        logger.warning("Failed to send warning to user %s", service.owner_telegram_id)


async def _send_expired_message(bot, service, time_expired: bool, traffic_expired: bool):
    """Send expired message to user."""
    lines = ["⛔ سرویس شما به اتمام رسیده است!\n"]

    if time_expired:
        lines.append("📅 زمان سرویس تمام شده است.")

    if traffic_expired:
        lines.append("🌐 ترافیک سرویس تمام شده است.")

    lines.append("\nبرای تمدید یا خرید سرویس جدید، از منوی اصلی استفاده کنید.")

    try:
        await bot.send_message(service.owner_telegram_id, "\n".join(lines))
    except Exception:
        logger.warning("Failed to send expired message to user %s", service.owner_telegram_id)


async def _scheduler_loop(bot):
    """Background loop that checks services at scheduled times."""
    while True:
        now = datetime.now(timezone.utc)
        # Find next check time
        next_check = None
        for hour in CHECK_HOURS:
            target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            if next_check is None or target < next_check:
                next_check = target

        if next_check:
            wait_seconds = (next_check - now).total_seconds()
            logger.info("Next service check at %s (in %.0f seconds)", next_check.isoformat(), wait_seconds)
            await asyncio.sleep(wait_seconds)

        logger.info("Running service expiry/traffic check...")
        try:
            await _check_services(bot)
        except Exception:
            logger.exception("Error during service check")

        logger.info("Running panel traffic check...")
        try:
            await _check_panel_traffic(bot)
        except Exception:
            logger.exception("Error during panel traffic check")

        logger.info("Running Xenet balance check...")
        try:
            await _check_xenet_balance(bot)
        except Exception:
            logger.exception("Error during Xenet balance check")

        # Sleep a bit after check to avoid running twice in the same minute
        await asyncio.sleep(60)


def start_scheduler(bot):
    """Start the background scheduler."""
    asyncio.create_task(_scheduler_loop(bot))
    logger.info("Service scheduler started")
