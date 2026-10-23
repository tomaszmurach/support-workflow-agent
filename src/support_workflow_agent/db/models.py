from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Text,
    UniqueConstraint,
    Uuid,
    and_,
    func,
    text,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from support_workflow_agent.db.base import Base


class OrderStatus(StrEnum):
    PLACED = "PLACED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class TicketStatus(StrEnum):
    OPEN = "OPEN"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    display_name: Mapped[str] = mapped_column(Text)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("id", "customer_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    order_number: Mapped[str] = mapped_column(Text, unique=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            name="order_status",
            length=32,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        )
    )
    promised_delivery_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship()


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        ForeignKeyConstraint(["order_id", "customer_id"], ["orders.id", "orders.customer_id"]),
        CheckConstraint("version > 0", name="version_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"))
    order_id: Mapped[UUID | None] = mapped_column(Uuid)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(
            TicketStatus,
            name="ticket_status",
            length=32,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        )
    )
    version: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )

    customer: Mapped[Customer] = relationship(foreign_keys=[customer_id])
    # Loading checks both keys; assignment only writes order_id. A mismatched
    # order must fail the FK check, never silently change the ticket's owner.
    order: Mapped[Order | None] = relationship(
        primaryjoin=lambda: and_(
            Order.id == foreign(Ticket.order_id), Order.customer_id == Ticket.customer_id
        ),
    )
