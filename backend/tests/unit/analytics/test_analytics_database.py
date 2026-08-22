"""Connection setup failures and query failures must remain distinguishable."""

import pytest

from app.analytics.connection import AnalyticsDatabase


class _Connection:
    async def close(self) -> None:
        pass


class _Engine:
    async def connect(self) -> _Connection:
        return _Connection()


@pytest.mark.asyncio
async def test_query_error_is_not_relabelled_as_database_unavailable() -> None:
    database = AnalyticsDatabase("postgresql+asyncpg://configured")
    database._get_engine = lambda: _Engine()  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="invalid column"):
        async with database.connection():
            raise ValueError("invalid column")
