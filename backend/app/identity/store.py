"""Persistence for users, sessions, and recovery/verification tokens.

Follows the same shape as ``app.reports.store``: an abstract contract naming
the operations, an in-process implementation for tests and zero-config
development, and one PostgreSQL implementation for a real deployment,
selected the same way ``MEMORY_BACKEND``/``ARTIFACT_BACKEND`` already select
between their own two implementations.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update

from app.db.records import IdentityTokenRecord, SessionRecord, UserRecord
from app.db.session import Database
from app.identity.contracts import IdentityToken, Session, TokenPurpose, User


def _now() -> datetime:
    return datetime.now(UTC)


# -- user store ---------------------------------------------------------


class UserStore(ABC):
    @abstractmethod
    async def create(self, *, email: str, display_name: str, password_hash: str) -> User:
        """``email`` must already be normalized; uniqueness is enforced here."""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """``email`` must already be normalized -- this performs an exact match."""

    @abstractmethod
    async def update_password_hash(self, user_id: UUID, password_hash: str) -> None: ...

    @abstractmethod
    async def mark_email_verified(self, user_id: UUID) -> None: ...

    @abstractmethod
    async def record_login(self, user_id: UUID, *, at: datetime) -> None: ...

    @abstractmethod
    async def set_active(self, user_id: UUID, *, is_active: bool) -> None:
        """Enable or disable an account. No route exposes this in this phase;
        it exists for tests and for the account-management surface this
        foundation is built to support later.
        """

    @abstractmethod
    async def update_profile(
        self, user_id: UUID, *, display_name: str | None = None,
        preferred_timezone: str | None = None, preferred_locale: str | None = None,
    ) -> User | None:
        """Apply only the fields the caller actually supplied."""

    @abstractmethod
    async def set_profile_image(
        self, user_id: UUID, *, artifact_id: UUID | None, workspace_id: UUID | None,
    ) -> User | None:
        """Both ``None`` clears the image; both set together stores a new one."""

    @abstractmethod
    async def set_pending_email(self, user_id: UUID, *, pending_email: str | None) -> None:
        """Record (or, with ``None``, abandon) an email change awaiting confirmation."""

    @abstractmethod
    async def apply_email_change(self, user_id: UUID, *, new_email: str) -> User | None:
        """Redeem a confirmed change: ``email`` becomes ``new_email``, verified, pending cleared."""


def _user_to_domain(record: UserRecord) -> User:
    return User(
        id=record.id, email=record.email, display_name=record.display_name,
        password_hash=record.password_hash, is_active=record.is_active,
        email_verified=record.email_verified, pending_email=record.pending_email,
        preferred_timezone=record.preferred_timezone, preferred_locale=record.preferred_locale,
        profile_image_artifact_id=record.profile_image_artifact_id,
        profile_image_workspace_id=record.profile_image_workspace_id,
        created_at=record.created_at, updated_at=record.updated_at, last_login_at=record.last_login_at,
    )


class InMemoryUserStore(UserStore):
    """Concurrency-safe in-process store for development and tests."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}
        self._lock = asyncio.Lock()

    async def create(self, *, email: str, display_name: str, password_hash: str) -> User:
        async with self._lock:
            if any(existing.email == email for existing in self._users.values()):
                raise ValueError(f"Email already registered: {email}")
            now = _now()
            user = User(
                id=uuid4(), email=email, display_name=display_name, password_hash=password_hash,
                is_active=True, email_verified=False, created_at=now, updated_at=now, last_login_at=None,
            )
            self._users[user.id] = user
            return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        async with self._lock:
            return self._users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        async with self._lock:
            return next((user for user in self._users.values() if user.email == email), None)

    async def update_password_hash(self, user_id: UUID, password_hash: str) -> None:
        async with self._lock:
            existing = self._users.get(user_id)
            if existing is None:
                return
            self._users[user_id] = existing.model_copy(update={"password_hash": password_hash, "updated_at": _now()})

    async def mark_email_verified(self, user_id: UUID) -> None:
        async with self._lock:
            existing = self._users.get(user_id)
            if existing is None:
                return
            self._users[user_id] = existing.model_copy(update={"email_verified": True, "updated_at": _now()})

    async def record_login(self, user_id: UUID, *, at: datetime) -> None:
        async with self._lock:
            existing = self._users.get(user_id)
            if existing is None:
                return
            self._users[user_id] = existing.model_copy(update={"last_login_at": at})

    async def set_active(self, user_id: UUID, *, is_active: bool) -> None:
        async with self._lock:
            existing = self._users.get(user_id)
            if existing is None:
                return
            self._users[user_id] = existing.model_copy(update={"is_active": is_active, "updated_at": _now()})

    async def update_profile(
        self, user_id: UUID, *, display_name: str | None = None,
        preferred_timezone: str | None = None, preferred_locale: str | None = None,
    ) -> User | None:
        async with self._lock:
            existing = self._users.get(user_id)
            if existing is None:
                return None
            changes: dict[str, object] = {"updated_at": _now()}
            if display_name is not None:
                changes["display_name"] = display_name
            if preferred_timezone is not None:
                changes["preferred_timezone"] = preferred_timezone
            if preferred_locale is not None:
                changes["preferred_locale"] = preferred_locale
            updated = existing.model_copy(update=changes)
            self._users[user_id] = updated
            return updated

    async def set_profile_image(
        self, user_id: UUID, *, artifact_id: UUID | None, workspace_id: UUID | None,
    ) -> User | None:
        async with self._lock:
            existing = self._users.get(user_id)
            if existing is None:
                return None
            updated = existing.model_copy(update={
                "profile_image_artifact_id": artifact_id, "profile_image_workspace_id": workspace_id,
                "updated_at": _now(),
            })
            self._users[user_id] = updated
            return updated

    async def set_pending_email(self, user_id: UUID, *, pending_email: str | None) -> None:
        async with self._lock:
            existing = self._users.get(user_id)
            if existing is None:
                return
            self._users[user_id] = existing.model_copy(update={"pending_email": pending_email, "updated_at": _now()})

    async def apply_email_change(self, user_id: UUID, *, new_email: str) -> User | None:
        async with self._lock:
            existing = self._users.get(user_id)
            if existing is None:
                return None
            updated = existing.model_copy(update={
                "email": new_email, "pending_email": None, "email_verified": True, "updated_at": _now(),
            })
            self._users[user_id] = updated
            return updated


class PostgresUserStore(UserStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def close(self) -> None:
        """Release the connection pool this store owns, at application shutdown."""

        await self._database.dispose()

    async def create(self, *, email: str, display_name: str, password_hash: str) -> User:
        now = _now()
        record = UserRecord(
            id=uuid4(), email=email, display_name=display_name, password_hash=password_hash,
            is_active=True, email_verified=False, created_at=now, updated_at=now, last_login_at=None,
        )
        async with self._database.session() as session, session.begin():
            session.add(record)
        return _user_to_domain(record)

    async def get_by_id(self, user_id: UUID) -> User | None:
        async with self._database.session() as session:
            record = await session.get(UserRecord, user_id)
        return _user_to_domain(record) if record is not None else None

    async def get_by_email(self, email: str) -> User | None:
        async with self._database.session() as session:
            record = await session.scalar(select(UserRecord).where(UserRecord.email == email))
        return _user_to_domain(record) if record is not None else None

    async def update_password_hash(self, user_id: UUID, password_hash: str) -> None:
        async with self._database.session() as session, session.begin():
            record = await session.get(UserRecord, user_id)
            if record is None:
                return
            record.password_hash = password_hash
            record.updated_at = _now()

    async def mark_email_verified(self, user_id: UUID) -> None:
        async with self._database.session() as session, session.begin():
            record = await session.get(UserRecord, user_id)
            if record is None:
                return
            record.email_verified = True
            record.updated_at = _now()

    async def record_login(self, user_id: UUID, *, at: datetime) -> None:
        async with self._database.session() as session, session.begin():
            record = await session.get(UserRecord, user_id)
            if record is None:
                return
            record.last_login_at = at

    async def set_active(self, user_id: UUID, *, is_active: bool) -> None:
        async with self._database.session() as session, session.begin():
            record = await session.get(UserRecord, user_id)
            if record is None:
                return
            record.is_active = is_active
            record.updated_at = _now()

    async def update_profile(
        self, user_id: UUID, *, display_name: str | None = None,
        preferred_timezone: str | None = None, preferred_locale: str | None = None,
    ) -> User | None:
        async with self._database.session() as session, session.begin():
            record = await session.get(UserRecord, user_id)
            if record is None:
                return None
            if display_name is not None:
                record.display_name = display_name
            if preferred_timezone is not None:
                record.preferred_timezone = preferred_timezone
            if preferred_locale is not None:
                record.preferred_locale = preferred_locale
            record.updated_at = _now()
            return _user_to_domain(record)

    async def set_profile_image(
        self, user_id: UUID, *, artifact_id: UUID | None, workspace_id: UUID | None,
    ) -> User | None:
        async with self._database.session() as session, session.begin():
            record = await session.get(UserRecord, user_id)
            if record is None:
                return None
            record.profile_image_artifact_id = artifact_id
            record.profile_image_workspace_id = workspace_id
            record.updated_at = _now()
            return _user_to_domain(record)

    async def set_pending_email(self, user_id: UUID, *, pending_email: str | None) -> None:
        async with self._database.session() as session, session.begin():
            record = await session.get(UserRecord, user_id)
            if record is None:
                return
            record.pending_email = pending_email
            record.updated_at = _now()

    async def apply_email_change(self, user_id: UUID, *, new_email: str) -> User | None:
        async with self._database.session() as session, session.begin():
            record = await session.get(UserRecord, user_id)
            if record is None:
                return None
            record.email = new_email
            record.pending_email = None
            record.email_verified = True
            record.updated_at = _now()
            return _user_to_domain(record)


# -- session store --------------------------------------------------------


class SessionStore(ABC):
    @abstractmethod
    async def create(
        self, *, user_id: UUID, token_hash: str, csrf_token_hash: str, expires_at: datetime,
        user_agent: str | None, ip_address: str | None,
    ) -> Session: ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> Session | None: ...

    @abstractmethod
    async def touch(self, session_id: UUID, *, last_seen_at: datetime) -> None:
        """Refresh the sliding idle-timeout clock. Not a security-relevant mutation."""

    @abstractmethod
    async def revoke(self, session_id: UUID) -> None: ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: UUID, *, except_session_id: UUID | None = None) -> int:
        """Revoke every live session for ``user_id``, returning how many were revoked."""


def _session_to_domain(record: SessionRecord) -> Session:
    return Session(
        id=record.id, user_id=record.user_id, token_hash=record.token_hash,
        csrf_token_hash=record.csrf_token_hash, created_at=record.created_at,
        expires_at=record.expires_at, last_seen_at=record.last_seen_at,
        revoked_at=record.revoked_at, user_agent=record.user_agent, ip_address=record.ip_address,
    )


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._sessions: dict[UUID, Session] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, *, user_id: UUID, token_hash: str, csrf_token_hash: str, expires_at: datetime,
        user_agent: str | None, ip_address: str | None,
    ) -> Session:
        async with self._lock:
            now = _now()
            session = Session(
                id=uuid4(), user_id=user_id, token_hash=token_hash, csrf_token_hash=csrf_token_hash,
                created_at=now, expires_at=expires_at, last_seen_at=now, revoked_at=None,
                user_agent=user_agent, ip_address=ip_address,
            )
            self._sessions[session.id] = session
            return session

    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        async with self._lock:
            return next((item for item in self._sessions.values() if item.token_hash == token_hash), None)

    async def touch(self, session_id: UUID, *, last_seen_at: datetime) -> None:
        async with self._lock:
            existing = self._sessions.get(session_id)
            if existing is None:
                return
            self._sessions[session_id] = existing.model_copy(update={"last_seen_at": last_seen_at})

    async def revoke(self, session_id: UUID) -> None:
        async with self._lock:
            existing = self._sessions.get(session_id)
            if existing is None:
                return
            self._sessions[session_id] = existing.model_copy(update={"revoked_at": _now()})

    async def revoke_all_for_user(self, user_id: UUID, *, except_session_id: UUID | None = None) -> int:
        async with self._lock:
            now = _now()
            count = 0
            for session_id, existing in list(self._sessions.items()):
                if existing.user_id != user_id or existing.revoked_at is not None:
                    continue
                if except_session_id is not None and session_id == except_session_id:
                    continue
                self._sessions[session_id] = existing.model_copy(update={"revoked_at": now})
                count += 1
            return count


class PostgresSessionStore(SessionStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def close(self) -> None:
        await self._database.dispose()

    async def create(
        self, *, user_id: UUID, token_hash: str, csrf_token_hash: str, expires_at: datetime,
        user_agent: str | None, ip_address: str | None,
    ) -> Session:
        now = _now()
        record = SessionRecord(
            id=uuid4(), user_id=user_id, token_hash=token_hash, csrf_token_hash=csrf_token_hash,
            created_at=now, expires_at=expires_at, last_seen_at=now, revoked_at=None,
            user_agent=user_agent, ip_address=ip_address,
        )
        async with self._database.session() as session, session.begin():
            session.add(record)
        return _session_to_domain(record)

    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        async with self._database.session() as session:
            record = await session.scalar(select(SessionRecord).where(SessionRecord.token_hash == token_hash))
        return _session_to_domain(record) if record is not None else None

    async def touch(self, session_id: UUID, *, last_seen_at: datetime) -> None:
        async with self._database.session() as session, session.begin():
            record = await session.get(SessionRecord, session_id)
            if record is None:
                return
            record.last_seen_at = last_seen_at

    async def revoke(self, session_id: UUID) -> None:
        async with self._database.session() as session, session.begin():
            record = await session.get(SessionRecord, session_id)
            if record is None:
                return
            record.revoked_at = _now()

    async def revoke_all_for_user(self, user_id: UUID, *, except_session_id: UUID | None = None) -> int:
        now = _now()
        async with self._database.session() as session, session.begin():
            query = select(SessionRecord).where(
                SessionRecord.user_id == user_id, SessionRecord.revoked_at.is_(None)
            )
            if except_session_id is not None:
                query = query.where(SessionRecord.id != except_session_id)
            records = (await session.scalars(query)).all()
            for record in records:
                record.revoked_at = now
        return len(records)


# -- identity token store --------------------------------------------------


class IdentityTokenStore(ABC):
    @abstractmethod
    async def create(
        self, *, user_id: UUID, token_hash: str, purpose: TokenPurpose, expires_at: datetime,
    ) -> IdentityToken: ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str, *, purpose: TokenPurpose) -> IdentityToken | None:
        """Return ``None`` if the hash is unknown or belongs to a different purpose."""

    @abstractmethod
    async def mark_used(self, token_id: UUID, *, at: datetime) -> None: ...

    @abstractmethod
    async def revoke_active_for_user(self, user_id: UUID, *, purpose: TokenPurpose) -> None:
        """Invalidate every outstanding, unused token of ``purpose`` before issuing a new one."""


def _token_to_domain(record: IdentityTokenRecord) -> IdentityToken:
    return IdentityToken(
        id=record.id, user_id=record.user_id, token_hash=record.token_hash,
        purpose=TokenPurpose(record.purpose), created_at=record.created_at,
        expires_at=record.expires_at, used_at=record.used_at, revoked_at=record.revoked_at,
    )


class InMemoryIdentityTokenStore(IdentityTokenStore):
    def __init__(self) -> None:
        self._tokens: dict[UUID, IdentityToken] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, *, user_id: UUID, token_hash: str, purpose: TokenPurpose, expires_at: datetime,
    ) -> IdentityToken:
        async with self._lock:
            token = IdentityToken(
                id=uuid4(), user_id=user_id, token_hash=token_hash, purpose=purpose,
                created_at=_now(), expires_at=expires_at, used_at=None, revoked_at=None,
            )
            self._tokens[token.id] = token
            return token

    async def get_by_token_hash(self, token_hash: str, *, purpose: TokenPurpose) -> IdentityToken | None:
        async with self._lock:
            return next(
                (item for item in self._tokens.values() if item.token_hash == token_hash and item.purpose is purpose),
                None,
            )

    async def mark_used(self, token_id: UUID, *, at: datetime) -> None:
        async with self._lock:
            existing = self._tokens.get(token_id)
            if existing is None:
                return
            self._tokens[token_id] = existing.model_copy(update={"used_at": at})

    async def revoke_active_for_user(self, user_id: UUID, *, purpose: TokenPurpose) -> None:
        async with self._lock:
            now = _now()
            for token_id, existing in list(self._tokens.items()):
                if existing.user_id != user_id or existing.purpose is not purpose:
                    continue
                if existing.used_at is not None or existing.revoked_at is not None:
                    continue
                self._tokens[token_id] = existing.model_copy(update={"revoked_at": now})


class PostgresIdentityTokenStore(IdentityTokenStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def close(self) -> None:
        await self._database.dispose()

    async def create(
        self, *, user_id: UUID, token_hash: str, purpose: TokenPurpose, expires_at: datetime,
    ) -> IdentityToken:
        record = IdentityTokenRecord(
            id=uuid4(), user_id=user_id, token_hash=token_hash, purpose=purpose.value,
            created_at=_now(), expires_at=expires_at, used_at=None, revoked_at=None,
        )
        async with self._database.session() as session, session.begin():
            session.add(record)
        return _token_to_domain(record)

    async def get_by_token_hash(self, token_hash: str, *, purpose: TokenPurpose) -> IdentityToken | None:
        async with self._database.session() as session:
            record = await session.scalar(
                select(IdentityTokenRecord).where(
                    IdentityTokenRecord.token_hash == token_hash, IdentityTokenRecord.purpose == purpose.value,
                )
            )
        return _token_to_domain(record) if record is not None else None

    async def mark_used(self, token_id: UUID, *, at: datetime) -> None:
        async with self._database.session() as session, session.begin():
            record = await session.get(IdentityTokenRecord, token_id)
            if record is None:
                return
            record.used_at = at

    async def revoke_active_for_user(self, user_id: UUID, *, purpose: TokenPurpose) -> None:
        now = _now()
        async with self._database.session() as session, session.begin():
            await session.execute(
                update(IdentityTokenRecord)
                .where(
                    IdentityTokenRecord.user_id == user_id, IdentityTokenRecord.purpose == purpose.value,
                    IdentityTokenRecord.used_at.is_(None), IdentityTokenRecord.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
