"""Developer-only command for safe external analytics schema discovery.

Run: python -m app.analytics.inspect [table_name]
"""

import asyncio
import sys

from app.analytics import AnalyticsDatabase, PostgreSQLInspector
from app.analytics.database import AnalyticsDatabaseError
from app.analytics.allowlist import AnalyticsSchemaPolicy
from app.config import Settings


async def main() -> int:
    settings = Settings()
    database = AnalyticsDatabase(settings.analytics_database_url)
    inspector = PostgreSQLInspector(database, AnalyticsSchemaPolicy.configured(settings.analytics_db_schema), cache_ttl_seconds=settings.analytics_schema_cache_ttl_seconds)
    try:
        summary = await inspector.list_tables()
        print("Connected to analytics database.")
        print(f"Tables discovered: {len(summary.tables)}")
        for table in summary.tables:
            print(table.name)
        if len(sys.argv) > 1:
            print()
            print(inspector and (await inspector.describe_table(sys.argv[1])).model_dump_json(indent=2, by_alias=True))
        return 0
    except AnalyticsDatabaseError as error:
        print(str(error))
        return 1
    finally:
        await database.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
