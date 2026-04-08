import uuid

from typing import Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

from app.domain.err import AlreadySentError


@dataclass
class Outbox:
    id: int = field(default=None, init=False)  # type: ignore[assignment]
    payment_id: uuid.UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc), init=False)
    sent_at: Optional[datetime] = field(default=None, init=False)

    def mark_sent(self):
        if self.sent_at:
            raise AlreadySentError(f"Message represented by outbox '{self.id}' already was delivered")
        self.sent_at = datetime.now(timezone.utc)
