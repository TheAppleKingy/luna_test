from sqlalchemy import (
    Table,
    Column,
    DateTime,
    Index,
    Integer
)
from sqlalchemy.dialects.postgresql import UUID

from .meta import metadata


outbox = Table(
    "outbox",
    metadata,
    Column("id", Integer, primary_key=True, unique=True, nullable=False, autoincrement=True),
    Column("payment_id", UUID(as_uuid=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("sent_at", DateTime(timezone=True), nullable=True),
)

Index(
    "idx_outbox_unprocessed",
    outbox.c.sent_at,
    outbox.c.created_at
)
