from sqlalchemy import (
    Table,
    Column,
    String,
    UUID,
    Numeric,
    Enum,
    DateTime
)
from sqlalchemy.dialects.postgresql import JSONB

from app.domain.entities import (
    Currency,
    Status
)
from .meta import metadata

payments = Table(
    "payments",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("amount", Numeric(precision=10, scale=2), nullable=False),
    Column("currency", Enum(Currency), nullable=False),
    Column("description", String(500), nullable=False),
    Column("meta", JSONB, nullable=False),
    Column("status", Enum(Status), nullable=False, unique=False),
    Column("idempotency_key", String(255), nullable=False, unique=True),
    Column("webhook_url", String, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
