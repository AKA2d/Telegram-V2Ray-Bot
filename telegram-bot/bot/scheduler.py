"""Periodic service expiry, traffic warnings, and Xenet balance monitoring."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

CHECK_HOURS = [8, 12, 16]  # 8am, 12pm, 4pm
XENET_BALANCE_WARNING_THRESHOLD = 100  # Warn when balance is below this amount


@dataclass
class _EvalResult:
    """Result of evaluating a single service for notification needs."""
    is_expired: bool  # True = expired, False = warning
    time_flag: bool   # time-related issue (expired or expiring soon)
    traffic_flag: bool  # traffic-related issue (exhausted or nearly exhausted)
    time_detail: Optional[str] = None  # human-readable time detail (e.g. "2 days")
    traffic_detail: Optional[str] = None  # human-readable traffic detail


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


async def _check_services(bot, *, dry_run: bool = False):
    """Check all active services and send consolidated warnings per user.

    Instead of sending one message per service, services are grouped by
    owner and a single message is sent per user listing all their services
    that need attention.

    When *dry_run* is ``True`` the evaluation and sending still happen, but
    the dedup timestamps (``last_warning_sent_at`` / ``last_expired_sent_at``)
    are **not** written to the database so that real notifications are not
    suppressed afterwards.
    """
    from collections import defaultdict

    from .db import async_session
    from .models import Service
    from .services_repo import update_service
    from sqlalchemy import select

    now = datetime.now(timezone.utc)

    async with async_session() as session:
        result = await session.execute(
            select(Service).where(Service.status == "active")
        )
        services = result.scalars().all()

    # --- Evaluate every service and group results by owner ---
    # Each entry: {owner_id: [(_EvalResult, service), ...]}
    user_results: dict[int, list[tuple[_EvalResult, Service]]] = defaultdict(list)

    for service in services:
        try:
            eval_result = await _evaluate_service(service, now)
            if eval_result is not None:
                user_results[service.owner_telegram_id].append((eval_result, service))
        except Exception:
            logger.exception("Error evaluating service %s", service.id)

    # --- Send one consolidated message per user ---
    for owner_id, entries in user_results.items():
        try:
            await _send_user_notification(bot, owner_id, entries)
            # Record timestamps for every service that was included
            if not dry_run:
                now_ts = datetime.now(timezone.utc)
                for eval_result, service in entries:
                    if eval_result.is_expired:
                        await update_service(service.id, last_expired_sent_at=now_ts)
                    else:
                        await update_service(service.id, last_warning_sent_at=now_ts)
        except Exception:
            logger.exception("Error sending consolidated notification to user %s", owner_id)


async def _evaluate_service(service, now: datetime) -> Optional[_EvalResult]:
    """Evaluate a single service and return its notification needs.

    Returns ``None`` if the service does not need any notification (either
    because nothing is wrong, or because the admin has disabled that
    notification type, or because the notification was already sent and
    the service has not been renewed since).
    """
    from .panel_client import PanelAPIError, panel_client
    from .settings_repo import get_setting
    from .xenet_client import XenetAPIError, xenet_client

    # --- Read admin notification settings ---
    settings_time_warning = (await get_setting("notify_time_warning")) == "1"
    settings_time_expired = (await get_setting("notify_time_expired")) == "1"
    settings_traffic_warning = (await get_setting("notify_traffic_warning")) == "1"
    settings_traffic_expired = (await get_setting("notify_traffic_expired")) == "1"

    # --- Determine current warning / expired flags ---
    time_warning = False
    time_expired = False
    time_detail: Optional[str] = None
    if service.expires_at:
        expires = service.expires_at if service.expires_at.tzinfo else service.expires_at.replace(tzinfo=timezone.utc)
        created = service.created_at.replace(tzinfo=timezone.utc) if service.created_at.tzinfo is None else service.created_at
        if expires <= now:
            time_expired = True
            time_detail = "زمان سرویس تمام شده"
        else:
            remaining = (expires - now).total_seconds()
            total = (expires - created).total_seconds()
            if total > 0 and remaining / total <= 0.1:
                time_warning = True
                remaining_days = (expires - now).days
                if service.service_type == "unlimited" and service.xenet_account_id:
                    try:
                        xenet_config = await xenet_client.get_v2_account(service.xenet_account_id)
                        days_left = xenet_config.get("days_left", 0)
                        time_detail = f"{days_left} روز باقی‌مانده"
                    except XenetAPIError:
                        time_detail = "کمتر از ۳ روز باقی‌مانده"
                else:
                    time_detail = f"{remaining_days} روز باقی‌مانده"

    traffic_warning = False
    traffic_expired = False
    traffic_detail: Optional[str] = None
    if service.service_type != "unlimited":
        try:
            panel_user = await panel_client.get_user(service.panel_username)
            bytes_used = (panel_user.raw.get("usage")
                          or panel_user.raw.get("data_usage")
                          or panel_user.raw.get("used_traffic") or 0)
            total_bytes = float(service.traffic_gb) * 1024 ** 3
            if total_bytes > 0:
                usage_ratio = bytes_used / total_bytes
                used_gb = bytes_used / (1024**3)
                if usage_ratio >= 1.0:
                    traffic_expired = True
                    traffic_detail = f"ترافیک تمام شده \n🪫 ({used_gb:.1f} از {service.traffic_gb} گیگ)\n"
                elif usage_ratio >= 0.9:
                    traffic_warning = True
                    traffic_detail = f"ترافیک در حال اتمام است \n🪫 {used_gb:.1f} از {service.traffic_gb}\n"
        except PanelAPIError:
            pass
    else:
        if service.xenet_account_id:
            try:
                xenet_config = await xenet_client.get_v2_account(service.xenet_account_id)
                days_left = xenet_config.get("days_left", 30)
                if days_left <= 0:
                    time_expired = True
                    time_detail = "\nزمان سرویس تمام شده\n"
                elif days_left <= 3:
                    time_warning = True
                    time_detail = f"\n{days_left} روز باقی‌مانده\n"
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

    if not wants_expired and not wants_warning:
        return None

    # --- Deduplication ---
    # Expired: only re-send after the service has been renewed (new expires_at > last sent)
    if wants_expired:
        last = service.last_expired_sent_at
        if last is not None and (not service.expires_at or service.expires_at <= last):
            return None
    # Warning: send at most once per service lifetime (reset on renewal)
    elif wants_warning:
        if service.last_warning_sent_at is not None:
            return None

    return _EvalResult(
        is_expired=wants_expired,
        time_flag=time_expired or time_warning,
        traffic_flag=traffic_expired or traffic_warning,
        time_detail=time_detail,
        traffic_detail=traffic_detail,
    )


async def _send_user_notification(bot, owner_id: int, entries: list[tuple[_EvalResult, Service]]) -> None:
    """Send a single consolidated notification listing all affected services."""
    # Separate into expired vs warning buckets
    expired_entries = [(ev, svc) for ev, svc in entries if ev.is_expired]
    warning_entries = [(ev, svc) for ev, svc in entries if not ev.is_expired]

    parts: list[str] = []

    if expired_entries:
        parts.append("⛔ سرویس‌های شما به اتمام رسیده است:")
        for ev, svc in expired_entries:
            svc_label = svc.panel_username or f"سرویس #{svc.id}"
            details = []
            if ev.time_detail:
                details.append(f"\n📅 {ev.time_detail}")
            if ev.traffic_detail:
                details.append(f"\n🌐 {ev.traffic_detail}")
            detail_str = " — ".join(details) if details else ""
            parts.append(f"\n  • {svc_label}{(' — ' + detail_str) if detail_str else ''}")
        parts.append("\nبرای تمدید یا خرید سرویس جدید، از منوی اصلی استفاده کنید.")

    if warning_entries:
        parts.append("\n⚠️ سرویس‌های شما در حال اتمام است:")
        for ev, svc in warning_entries:
            svc_label = svc.panel_username or f"سرویس #{svc.id}"
            details = []
            if ev.time_detail:
                details.append(f"📅 {ev.time_detail}")
            if ev.traffic_detail:
                details.append(f"🌐 {ev.traffic_detail}")
            detail_str = " — ".join(details) if details else ""
            parts.append(f"\n  • {svc_label}{(' — ' + detail_str) if detail_str else ''}")
        parts.append("\nبرای تمدید سرویس، از منوی مدیریت سرویس استفاده کنید.")

    if not parts:
        return

    message = "\n".join(parts)

    try:
        await bot.send_message(owner_id, message)
    except Exception:
        logger.warning("Failed to send consolidated notification to user %s", owner_id)


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
