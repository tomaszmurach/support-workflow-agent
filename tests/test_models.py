import warnings
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import CheckConstraint, Uuid, create_engine, inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, SAWarning, StatementError
from sqlalchemy.orm import Session, configure_mappers
from sqlalchemy.schema import CreateTable

from support_workflow_agent.db.base import Base
from support_workflow_agent.db.models import Customer, Order, OrderStatus, Ticket, TicketStatus

CUSTOMER_ID = UUID(int=1)
OTHER_CUSTOMER_ID = UUID(int=2)
ORDER_ID = UUID(int=3)
TICKET_ID = UUID(int=4)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        Base.metadata.create_all(connection)
        connection.commit()
        with Session(connection) as session:
            session.add_all(
                [
                    Customer(id=CUSTOMER_ID, display_name="Synthetic customer"),
                    Customer(id=OTHER_CUSTOMER_ID, display_name="Other synthetic customer"),
                ]
            )
            session.flush()
            session.add(
                Order(
                    id=ORDER_ID,
                    order_number="ORD-1042",
                    customer_id=CUSTOMER_ID,
                    status=OrderStatus.SHIPPED,
                    promised_delivery_at=datetime(2026, 10, 21, tzinfo=UTC),
                )
            )
            session.commit()
            yield session
    engine.dispose()


def test_mappings_have_no_warnings_or_overlapping_writes() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", SAWarning)
        configure_mappers()
    mapper = inspect(Ticket)
    assert [target.name for _, target in mapper.relationships.order.synchronize_pairs] == [
        "order_id"
    ]
    assert [target.name for _, target in mapper.relationships.customer.synchronize_pairs] == [
        "customer_id"
    ]
    assert "orders.customer_id = tickets.customer_id" in str(mapper.relationships.order.primaryjoin)


def test_metadata_types_nullability_and_constraint_names() -> None:
    assert set(Base.metadata.tables) == {"customers", "orders", "tickets"}
    expected_names = {
        "pk_customers",
        "pk_orders",
        "pk_tickets",
        "uq_orders_order_number",
        "uq_orders_id_customer_id",
        "fk_orders_customer_id_customers",
        "fk_tickets_customer_id_customers",
        "fk_tickets_order_id_customer_id_orders",
        "ck_orders_order_status",
        "ck_tickets_ticket_status",
        "ck_tickets_version_positive",
    }
    assert {c.name for table in Base.metadata.tables.values() for c in table.constraints} == (
        expected_names
    )
    for model in (Customer, Order, Ticket):
        table = model.__table__
        assert list(table.primary_key.columns.keys()) == ["id"]
        assert isinstance(table.c.id.type, Uuid)
        assert table.c.id.type.as_uuid
        assert table.c.id.default.is_callable
        for column in table.columns:
            assert column.nullable == (column.name in {"order_id", "delivered_at"})
    for name in ("promised_delivery_at", "delivered_at"):
        assert Order.__table__.c[name].type.timezone
    assert "is_delayed" not in Order.__table__.c
    assert Ticket.__table__.c.version.default.arg == 1
    assert str(Ticket.__table__.c.version.server_default.arg) == "1"
    created_at = Ticket.__table__.c.created_at
    assert created_at.type.timezone
    assert created_at.nullable is False
    assert created_at.default is None
    assert str(created_at.server_default.arg) == "CURRENT_TIMESTAMP"


def test_composite_foreign_key_and_unique_target() -> None:
    table = Ticket.__table__
    constraint = next(c for c in table.foreign_key_constraints if len(c.columns) == 2)
    assert list(constraint.columns.keys()) == ["order_id", "customer_id"]
    assert [e.target_fullname for e in constraint.elements] == ["orders.id", "orders.customer_id"]
    unique = next(c for c in Order.__table__.constraints if c.name == "uq_orders_id_customer_id")
    assert list(unique.columns.keys()) == ["id", "customer_id"]


@pytest.mark.parametrize(
    ("model", "enum_class", "values"),
    [
        (Order, OrderStatus, ["PLACED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]),
        (Ticket, TicketStatus, ["OPEN", "ESCALATED", "RESOLVED"]),
    ],
)
def test_status_checks_compile_for_postgresql(model, enum_class, values) -> None:
    status_type = model.__table__.c.status.type
    assert status_type.enum_class is enum_class
    assert status_type.enums == values
    assert status_type.native_enum is False
    assert status_type.create_constraint is True
    assert status_type.validate_strings is True
    assert status_type.length == 32
    assert any(isinstance(c, CheckConstraint) for c in model.__table__.constraints)
    ddl = str(CreateTable(model.__table__).compile(dialect=postgresql.dialect()))
    assert "id UUID NOT NULL" in ddl
    assert "status VARCHAR(32) NOT NULL" in ddl
    assert "CHECK (status IN (" in ddl
    for value in values:
        assert f"'{value}'" in ddl


def test_postgresql_delivery_and_ownership_ddl() -> None:
    dialect = postgresql.dialect()
    order_ddl = str(CreateTable(Order.__table__).compile(dialect=dialect))
    ticket_ddl = str(CreateTable(Ticket.__table__).compile(dialect=dialect))
    assert "promised_delivery_at TIMESTAMP WITH TIME ZONE NOT NULL" in order_ddl
    assert "delivered_at TIMESTAMP WITH TIME ZONE" in order_ddl
    assert "UNIQUE (id, customer_id)" in order_ddl
    assert "FOREIGN KEY(order_id, customer_id) REFERENCES orders (id, customer_id)" in ticket_ddl
    assert "CHECK (version > 0)" in ticket_ddl
    assert "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL" in ticket_ddl


@pytest.mark.parametrize("linked", [True, False])
def test_ticket_round_trip_and_insert_defaults(session: Session, linked: bool) -> None:
    customer = session.get(Customer, CUSTOMER_ID)
    order = session.get(Order, ORDER_ID) if linked else None
    ticket = Ticket(
        customer=customer, order=order, message="Where is my order?", status=TicketStatus.OPEN
    )
    session.add(ticket)
    session.commit()
    session.expire_all()
    assert isinstance(ticket.id, UUID)
    assert ticket.version == 1
    assert isinstance(ticket.created_at, datetime)
    assert ticket.status is TicketStatus.OPEN
    assert ticket.customer is customer
    assert ticket.order is order
    assert ticket.customer_id == CUSTOMER_ID
    if linked:
        assert order.customer is customer
        assert order.status is OrderStatus.SHIPPED
        ticket.order = None
        session.commit()
        assert ticket.order_id is None
        assert ticket.customer_id == CUSTOMER_ID


def test_mismatched_order_assignment_does_not_rewrite_customer(session: Session) -> None:
    ticket = Ticket(
        customer=session.get(Customer, OTHER_CUSTOMER_ID),
        order=session.get(Order, ORDER_ID),
        message="Wrong owner",
        status=TicketStatus.OPEN,
    )
    session.add(ticket)
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        session.flush()
    assert ticket.customer_id == OTHER_CUSTOMER_ID
    session.rollback()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE orders SET customer_id = '00000000000000000000000000000009'",
        "UPDATE orders SET status = 'UNKNOWN'",
        "UPDATE tickets SET status = 'UNKNOWN'",
        "UPDATE tickets SET version = 0",
        "UPDATE tickets SET version = -1",
        "UPDATE tickets SET version = NULL",
        "UPDATE tickets SET created_at = NULL",
        "UPDATE tickets SET customer_id = '00000000000000000000000000000002'",
        "UPDATE tickets SET order_id = '00000000000000000000000000000009'",
        "UPDATE tickets SET order_id = NULL, customer_id = '00000000000000000000000000000009'",
        "UPDATE orders SET customer_id = '00000000000000000000000000000002'",
        "INSERT INTO orders (id, order_number, customer_id, status, promised_delivery_at) "
        "SELECT '00000000000000000000000000000009', order_number, customer_id, status, "
        "promised_delivery_at FROM orders",
    ],
)
def test_database_rejects_invalid_data_without_orm_validation(
    session: Session, statement: str
) -> None:
    session.add(
        Ticket(
            id=TICKET_ID,
            customer_id=CUSTOMER_ID,
            order_id=ORDER_ID,
            message="Delivery question",
            status=TicketStatus.OPEN,
        )
    )
    session.commit()
    with pytest.raises(IntegrityError):
        session.execute(text(statement))
    session.rollback()


def test_version_server_default_for_raw_insert(session: Session) -> None:
    session.execute(
        text(
            "INSERT INTO tickets (id, customer_id, message, status) "
            "VALUES (:id, :customer, :msg, :status)"
        ),
        {"id": TICKET_ID.hex, "customer": CUSTOMER_ID.hex, "msg": "Policy?", "status": "OPEN"},
    )
    session.commit()
    ticket = session.get(Ticket, TICKET_ID)
    assert ticket.version == 1
    assert ticket.order is None
    # SQLite returns a naive datetime even for DateTime(timezone=True).
    # This verifies database default execution, not PostgreSQL timezone semantics.
    assert isinstance(ticket.created_at, datetime)
    assert ticket.created_at.tzinfo is None
    created_at = ticket.created_at
    ticket.message = "Updated question"
    session.commit()
    session.refresh(ticket)
    assert ticket.created_at == created_at


def test_order_customer_foreign_key_without_referencing_tickets(session: Session) -> None:
    assert session.query(Ticket).count() == 0
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        session.execute(
            text("UPDATE orders SET customer_id = :missing_customer WHERE id = :order_id"),
            {"missing_customer": UUID(int=9).hex, "order_id": ORDER_ID.hex},
        )
    session.rollback()
    assert session.get(Order, ORDER_ID).customer_id == CUSTOMER_ID


@pytest.mark.parametrize("initially_linked", [True, False])
def test_persisted_ticket_rejects_cross_customer_order_and_restores_on_rollback(
    session: Session, initially_linked: bool
) -> None:
    original_order_id = ORDER_ID if initially_linked else None
    ticket = Ticket(
        id=TICKET_ID,
        customer_id=CUSTOMER_ID,
        order_id=original_order_id,
        message="Delivery question",
        status=TicketStatus.OPEN,
    )
    other_order = Order(
        id=UUID(int=5),
        customer_id=OTHER_CUSTOMER_ID,
        order_number="ORD-1043",
        status=OrderStatus.PLACED,
        promised_delivery_at=datetime(2026, 10, 22, tzinfo=UTC),
    )
    session.add_all([ticket, other_order])
    session.commit()
    assert inspect(ticket).persistent
    assert ticket.order_id == original_order_id

    ticket.order = other_order
    assert ticket.customer_id == CUSTOMER_ID
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        session.flush()
    session.rollback()

    assert ticket.customer_id == CUSTOMER_ID
    assert ticket.customer.id == CUSTOMER_ID
    assert ticket.order_id == original_order_id
    expected_order = session.get(Order, ORDER_ID) if initially_linked else None
    assert ticket.order is expected_order
    # A successful subsequent write confirms the session is usable after rollback.
    ticket.message = "Updated after rollback"
    session.commit()
    session.refresh(ticket)
    assert ticket.message == "Updated after rollback"
    assert ticket.customer_id == CUSTOMER_ID
    assert ticket.order_id == original_order_id


@pytest.mark.parametrize("model", [Order, Ticket])
def test_orm_rejects_unsupported_status_strings(session: Session, model: type[Base]) -> None:
    if model is Order:
        record = session.get(Order, ORDER_ID)
        original_status = OrderStatus.SHIPPED
    else:
        record = Ticket(
            id=TICKET_ID,
            customer_id=CUSTOMER_ID,
            message="Policy question",
            status=TicketStatus.OPEN,
        )
        session.add(record)
        session.commit()
        original_status = TicketStatus.OPEN

    record.status = "UNKNOWN"
    with pytest.raises(StatementError) as error:
        session.flush()
    assert isinstance(error.value.orig, LookupError)
    session.rollback()
    assert record.status is original_status
