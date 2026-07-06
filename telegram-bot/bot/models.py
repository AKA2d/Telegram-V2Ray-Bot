from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    wallet_balance: Mapped[Decimal] = mapped_column(Numeric(14, 0), default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    services: Mapped[list["Service"]] = relationship(back_populates="owner")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    panel_username: Mapped[str] = mapped_column(String(255), unique=True)
    panel_uuid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending_payment")
    user_count: Mapped[int] = mapped_column(Integer, default=1)
    months: Mapped[int] = mapped_column(Integer, default=1)
    traffic_gb: Mapped[int] = mapped_column(Integer, default=10)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 0), default=0)
    has_tunnel: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="services")
    orders: Mapped[list["Order"]] = relationship(back_populates="service")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    service_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("services.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(32))  # new_service | wallet_topup
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 0), default=0)
    status: Mapped[str] = mapped_column(String(32), default="awaiting_receipt")
    receipt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    card_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    admin_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="orders")
    service: Mapped["Service | None"] = relationship(back_populates="orders")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_number: Mapped[str] = mapped_column(String(64))
    holder_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    user_count: Mapped[int] = mapped_column(Integer, default=1)
    months: Mapped[int] = mapped_column(Integer, default=1)
    traffic_gb: Mapped[int] = mapped_column(Integer, default=10)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 0), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdminSetting(Base):
    __tablename__ = "admin_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class WalletAuditLog(Base):
    __tablename__ = "wallet_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    old_balance: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    new_balance: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    reason: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
