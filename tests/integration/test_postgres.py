from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import Connection, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from support_workflow_agent.db.models import Customer, Order, OrderStatus, Ticket, TicketStatus
from tests.postgres_support import migration_config, verify_empty_test_database

pytestmark = pytest.mark.postgres

CUSTOMER_ID = UUID(int=1)
OTHER_CUSTOMER_ID = UUID(int=2)
ORDER_ID = UUID(int=3)
TICKET_ID = UUID(int=4)
OTHER_ORDER_ID = UUID(int=5)
PROMISED = datetime(2026, 10, 23, 14, 30, tzinfo=timezone(timedelta(hours=2)))


@pytest.fixture
def records(pg_session: Session) -> Session:
    pg_session.add_all(
        [
            Customer(id=CUSTOMER_ID, display_name="Test customer"),
            Customer(id=OTHER_CUSTOMER_ID, display_name="Other test customer"),
        ]
    )
    pg_session.flush()
    pg_session.add_all(
        [
            Order(
                id=order_id,
                customer_id=customer_id,
                order_number=number,
                status=OrderStatus.SHIPPED,
                promised_delivery_at=PROMISED,
            )
            for order_id, customer_id, number in [
                (ORDER_ID, CUSTOMER_ID, "ORD-TEST-1"),
                (OTHER_ORDER_ID, OTHER_CUSTOMER_ID, "ORD-TEST-2"),
            ]
        ]
    )
    pg_session.flush()
    pg_session.add(
        Ticket(
            id=TICKET_ID,
            customer_id=CUSTOMER_ID,
            order_id=ORDER_ID,
            message="Delivery question",
            status=TicketStatus.OPEN,
        )
    )
    # Releases only the Session's savepoint; the fixture's outer transaction remains.
    pg_session.commit()
    return pg_session


def test_customer_fk_without_any_ticket(pg_session: Session) -> None:
    with pytest.raises(IntegrityError) as error, pg_session.begin_nested():
        pg_session.execute(
            text(
                "INSERT INTO orders (id, customer_id, order_number, status, promised_delivery_at) "
                "VALUES (:id, :customer, 'ORD-MISSING', 'PLACED', :promised)"
            ),
            {"id": ORDER_ID, "customer": CUSTOMER_ID, "promised": PROMISED},
        )
    assert error.value.orig.sqlstate == "23503"
    assert error.value.orig.diag.constraint_name == "fk_orders_customer_id_customers"
    assert pg_session.scalar(text("SELECT count(*) FROM orders")) == 0


@pytest.mark.parametrize(
    ("statement", "constraint"),
    [
        ("INSERT INTO customers (id, display_name) VALUES (:id, 'Duplicate')", "pk_customers"),
        (
            "INSERT INTO orders (id, order_number, customer_id, status, promised_delivery_at) "
            "VALUES (:id, 'ORD-DUPLICATE-PK', :customer, 'PLACED', :promised)",
            "pk_orders",
        ),
        (
            "INSERT INTO tickets (id, customer_id, message, status) "
            "VALUES (:id, :customer, 'Duplicate', 'OPEN')",
            "pk_tickets",
        ),
    ],
)
def test_duplicate_primary_keys(records: Session, statement: str, constraint: str) -> None:
    ids = {"pk_customers": CUSTOMER_ID, "pk_orders": ORDER_ID, "pk_tickets": TICKET_ID}
    with pytest.raises(IntegrityError) as error, records.begin_nested():
        records.execute(
            text(statement),
            {
                "id": ids[constraint],
                # Different customer and order number isolate the order PK from
                # the composite UNIQUE and order-number UNIQUE constraints.
                "customer": OTHER_CUSTOMER_ID,
                "promised": PROMISED,
            },
        )
    assert error.value.orig.sqlstate == "23505"
    assert error.value.orig.diag.constraint_name == constraint
    assert records.scalar(text("SELECT count(*) FROM customers")) == 2


@pytest.mark.parametrize("reference", ["orders", "tickets"])
def test_referenced_customer_cannot_be_deleted(pg_session: Session, reference: str) -> None:
    pg_session.add(Customer(id=CUSTOMER_ID, display_name="Referenced customer"))
    pg_session.flush()
    if reference == "orders":
        pg_session.add(
            Order(
                id=ORDER_ID,
                customer_id=CUSTOMER_ID,
                order_number="ORD-REFERENCED",
                status=OrderStatus.PLACED,
                promised_delivery_at=PROMISED,
            )
        )
    else:
        pg_session.add(
            Ticket(
                id=TICKET_ID,
                customer_id=CUSTOMER_ID,
                message="Policy question",
                status=TicketStatus.OPEN,
            )
        )
    pg_session.flush()
    # Exactly one referencing table exists, making the reported FK deterministic.
    with pytest.raises(IntegrityError) as error, pg_session.begin_nested():
        pg_session.execute(text("DELETE FROM customers WHERE id = :id"), {"id": CUSTOMER_ID})
    assert error.value.orig.sqlstate == "23503"
    assert error.value.orig.diag.constraint_name == f"fk_{reference}_customer_id_customers"
    assert pg_session.get(Customer, CUSTOMER_ID) is not None


@pytest.mark.parametrize(
    ("statement", "state", "constraint"),
    [
        (
            "UPDATE orders SET order_number = 'ORD-TEST-1' WHERE id = :other_order",
            "23505",
            "uq_orders_order_number",
        ),
        (
            "UPDATE tickets SET customer_id = :other_customer WHERE id = :ticket",
            "23503",
            "fk_tickets_order_id_customer_id_orders",
        ),
        (
            "UPDATE tickets SET order_id = :missing WHERE id = :ticket",
            "23503",
            "fk_tickets_order_id_customer_id_orders",
        ),
        (
            "UPDATE tickets SET order_id = NULL, customer_id = :missing WHERE id = :ticket",
            "23503",
            "fk_tickets_customer_id_customers",
        ),
        (
            "UPDATE orders SET customer_id = :other_customer WHERE id = :order",
            "23503",
            "fk_tickets_order_id_customer_id_orders",
        ),
        (
            "UPDATE orders SET status = 'UNKNOWN' WHERE id = :order",
            "23514",
            "ck_orders_order_status",
        ),
        (
            "UPDATE tickets SET status = 'UNKNOWN' WHERE id = :ticket",
            "23514",
            "ck_tickets_ticket_status",
        ),
        (
            "UPDATE tickets SET version = 0 WHERE id = :ticket",
            "23514",
            "ck_tickets_version_positive",
        ),
        (
            "UPDATE tickets SET version = -1 WHERE id = :ticket",
            "23514",
            "ck_tickets_version_positive",
        ),
    ],
)
def test_database_constraints(
    records: Session, statement: str, state: str, constraint: str
) -> None:
    # Raw SQL bypasses Enum.validate_strings so PostgreSQL must enforce the CHECKs.
    with pytest.raises(IntegrityError) as error, records.begin_nested():
        records.execute(
            text(statement),
            {
                "order": ORDER_ID,
                "ticket": TICKET_ID,
                "other_order": OTHER_ORDER_ID,
                "other_customer": OTHER_CUSTOMER_ID,
                "missing": UUID(int=99),
            },
        )
    assert error.value.orig.sqlstate == state
    assert error.value.orig.diag.constraint_name == constraint
    assert records.scalar(text("SELECT count(*) FROM tickets")) == 1


@pytest.mark.parametrize(
    ("table", "column", "row_id"),
    [("customers", column, CUSTOMER_ID) for column in ("id", "display_name")]
    + [
        ("orders", column, ORDER_ID)
        for column in ("id", "order_number", "customer_id", "status", "promised_delivery_at")
    ]
    + [
        ("tickets", column, TICKET_ID)
        for column in ("id", "customer_id", "message", "status", "version", "created_at")
    ],
)
def test_required_columns_reject_null(
    records: Session, table: str, column: str, row_id: UUID
) -> None:
    # Identifiers come solely from the fixed parameter list above.
    with pytest.raises(IntegrityError) as error, records.begin_nested():
        records.execute(text(f"UPDATE {table} SET {column} = NULL WHERE id = :id"), {"id": row_id})
    assert error.value.orig.sqlstate == "23502"
    assert error.value.orig.diag.column_name == column


def test_composite_unique_constraint_is_installed(pg_connection: Connection) -> None:
    # The PK also forbids duplicate id values, so an insert error cannot prove
    # this additional composite constraint exists. Inspect PostgreSQL's catalog.
    unique = {c["name"]: c for c in inspect(pg_connection).get_unique_constraints("orders")}
    assert unique["uq_orders_id_customer_id"]["column_names"] == ["id", "customer_id"]
    fk = next(
        c
        for c in inspect(pg_connection).get_foreign_keys("tickets")
        if c["name"] == "fk_tickets_order_id_customer_id_orders"
    )
    assert fk["constrained_columns"] == ["order_id", "customer_id"]
    assert fk["referred_table"] == "orders"
    assert fk["referred_columns"] == ["id", "customer_id"]


def test_uuid_timestamps_relationships_and_server_defaults(records: Session) -> None:
    order = records.get(Order, ORDER_ID)
    ticket = records.get(Ticket, TICKET_ID)
    assert isinstance(order.id, UUID)
    assert order.id == ORDER_ID
    assert ticket.order is order
    assert ticket.customer is order.customer
    assert order.promised_delivery_at.utcoffset() is not None
    assert order.promised_delivery_at.astimezone(UTC) == PROMISED.astimezone(UTC)
    assert order.delivered_at is None
    order.delivered_at = PROMISED + timedelta(hours=3)
    records.flush()
    records.expire_all()
    assert order.delivered_at.utcoffset() is not None
    assert order.delivered_at == PROMISED + timedelta(hours=3)
    assert ticket.created_at.utcoffset() is not None
    assert ticket.created_at == records.scalar(text("SELECT CURRENT_TIMESTAMP"))
    assert ticket.version == 1

    # Explicit raw INSERT proves defaults originate in PostgreSQL, not Python.
    inserted = records.execute(
        text(
            "INSERT INTO tickets (id, customer_id, message, status) "
            "VALUES (:id, :customer, 'Policy question', 'OPEN') "
            "RETURNING id, version, created_at, order_id"
        ),
        {"id": UUID(int=6), "customer": CUSTOMER_ID},
    ).one()
    assert isinstance(inserted.id, UUID)
    assert inserted.version == 1
    assert inserted.order_id is None
    assert inserted.created_at.utcoffset() is not None
    assert inserted.created_at == records.scalar(text("SELECT CURRENT_TIMESTAMP"))
    created_at = ticket.created_at
    ticket.message = "Follow-up"
    ticket.order = None
    records.commit()
    records.refresh(ticket)
    assert ticket.order is None
    assert ticket.customer_id == CUSTOMER_ID
    assert ticket.created_at == created_at


@pytest.mark.parametrize("status", list(OrderStatus) + list(TicketStatus))
def test_enum_round_trip(records: Session, status: OrderStatus | TicketStatus) -> None:
    model, row_id, table = (
        (Order, ORDER_ID, "orders")
        if isinstance(status, OrderStatus)
        else (Ticket, TICKET_ID, "tickets")
    )
    record = records.get(model, row_id)
    # Persist a different starting status even when the requested target is the
    # fixture's initial SHIPPED/OPEN status. The target assignment must update.
    baseline = next(member for member in type(status) if member != status)
    record.status = baseline
    records.flush()
    records.expire(record)
    assert record.status is baseline
    record.status = status
    records.flush()
    records.expire(record)
    assert record.status is status
    assert (
        records.scalar(text(f"SELECT status FROM {table} WHERE id = :id"), {"id": row_id})
        == status.value
    )


def test_persisted_order_assignment_rejected_without_rewriting_customer(records: Session) -> None:
    ticket = records.get(Ticket, TICKET_ID)
    other_order = records.get(Order, OTHER_ORDER_ID)
    with pytest.raises(IntegrityError) as error, records.begin_nested():
        ticket.order = other_order
        records.flush()
    assert error.value.orig.sqlstate == "23503"
    assert error.value.orig.diag.constraint_name == "fk_tickets_order_id_customer_id_orders"
    records.refresh(ticket)
    assert ticket.customer_id == CUSTOMER_ID
    assert ticket.order_id == ORDER_ID


def schema_snapshot(connection: Connection) -> dict[str, dict[str, object]]:
    """Capture stable schema properties, excluding OIDs and reflection ordering."""
    inspector = inspect(connection)
    snapshot = {}
    for table in sorted(inspector.get_table_names(schema="public")):
        pk = inspector.get_pk_constraint(table, schema="public")
        snapshot[table] = {
            "columns": [
                (
                    column["name"],
                    str(column["type"].compile(dialect=connection.dialect)),
                    column["nullable"],
                    " ".join(column["default"].split()) if column["default"] is not None else None,
                )
                for column in inspector.get_columns(table, schema="public")
            ],
            "primary_key": (pk["name"], tuple(pk["constrained_columns"])),
            "foreign_keys": sorted(
                (
                    fk["name"],
                    tuple(fk["constrained_columns"]),
                    fk["referred_schema"] or "public",
                    fk["referred_table"],
                    tuple(fk["referred_columns"]),
                    tuple(sorted(fk.get("options", {}).items())),
                )
                for fk in inspector.get_foreign_keys(table, schema="public")
            ),
            "unique": sorted(
                (unique["name"], tuple(unique["column_names"]))
                for unique in inspector.get_unique_constraints(table, schema="public")
            ),
            "checks": sorted(
                (check["name"], " ".join(check["sqltext"].split()))
                for check in inspector.get_check_constraints(table, schema="public")
            ),
        }
    return snapshot


def test_migration_lifecycle(pg_database: Connection) -> None:
    # This fixture starts empty. All lifecycle DDL stays inside a savepoint and
    # is rolled back even if an assertion fails; no committed schema is reset.
    savepoint = pg_database.begin_nested()
    try:
        config = migration_config(pg_database)
        verify_empty_test_database(pg_database)
        command.upgrade(config, "head")
        expected = {"customers", "orders", "tickets", "alembic_version"}
        assert set(inspect(pg_database).get_table_names()) == expected
        assert pg_database.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
        first_schema = schema_snapshot(pg_database)
        command.downgrade(migration_config(pg_database), "base")
        assert not {"customers", "orders", "tickets"} & set(inspect(pg_database).get_table_names())
        assert pg_database.scalar(
            text("SELECT extversion FROM pg_extension WHERE extname='vector'")
        )
        command.upgrade(migration_config(pg_database), "head")
        assert set(inspect(pg_database).get_table_names()) == expected
        assert pg_database.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
        assert schema_snapshot(pg_database) == first_schema
    finally:
        savepoint.rollback()
