"""Outbound identity email: an interface plus a safe local-development sender.

Nothing in this codebase has sent email before ``app.delivery.providers``'
SMTP client, which exists to hand a *finished report artifact* to its
destination on the scheduler's clock. This is deliberately separate:
identity email is triggered by direct user action (register, forgot
password), never carries an attachment, and must exist even when no SMTP
provider is configured, so registration and recovery still work in
development.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.core.logging import log_event

_logger = logging.getLogger(__name__)


class EmailMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    to: str
    subject: str
    body: str


class EmailSender(ABC):
    @abstractmethod
    async def send(self, message: EmailMessage) -> None:
        """Deliver ``message``. Implementations must never log its body."""


class FileEmailSender(EmailSender):
    """Write each message to a local outbox file instead of a real mail provider.

    This is a development stand-in, not a queue. Messages are written to disk
    -- never through the structured ``logging`` module -- so a password-reset
    or verification link stays inspectable during development without a raw
    token ever entering application logs. ``sent`` additionally keeps each
    message in process, so a test can assert on outbox content without
    parsing files.
    """

    def __init__(self, outbox_dir: Path) -> None:
        self._outbox_dir = outbox_dir
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)
        self._outbox_dir.mkdir(parents=True, exist_ok=True)
        path = self._outbox_dir / f"{len(self.sent):04d}-{_safe_filename(message.to)}.eml"
        path.write_text(f"To: {message.to}\nSubject: {message.subject}\n\n{message.body}\n")
        log_event(_logger, logging.INFO, "identity_email_queued", to=message.to, subject=message.subject)


def _safe_filename(value: str) -> str:
    return "".join(character if character.isalnum() or character in "@.-_" else "_" for character in value)
