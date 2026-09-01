"""Give already-written artifact files a durable record.

Run: python -m scripts.backfill_artifacts [--apply]

Before the registry moved to PostgreSQL, records lived in the process that made
them and the files were laid out as ``artifacts/<run_id>/<artifact_id>-<name>``.
Restarting lost every record while leaving the files behind, so a workspace can
hold artifacts nothing can hand out. Their run and artifact identifiers are
still in the path and their bytes are still on disk, so a record can be rebuilt
exactly — including the identifier, which means the original download URL works
again rather than a new one being minted.

Files already in the current ``<artifact_id>/<filename>`` layout are skipped:
those were written by a store that recorded them. Nothing is moved or renamed,
and a row that already exists is left alone, so this is safe to run twice.

Reads the workspace and database from the ordinary settings. Prints what it
would do and changes nothing unless ``--apply`` is passed.
"""

import asyncio
import mimetypes
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

#: ``<artifact_id>-<filename>``, the layout that predates durable records. The
#: identifier is a UUID, so the split is unambiguous even when a filename
#: contains a hyphen.
LEGACY_NAME = re.compile(
    r"^(?P<artifact_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})-(?P<filename>.+)$"
)


def _recoverable(area: Path) -> list[tuple[str, str, str, Path]]:
    """Return (run_id, artifact_id, filename, path) for each orphaned file."""

    found = []
    for path in sorted(area.glob("*/*")):
        if not path.is_file():
            continue  # A directory here is the current layout, already recorded.
        match = LEGACY_NAME.match(path.name)
        if match is None:
            continue
        found.append((path.parent.name, match["artifact_id"], match["filename"], path))
    return found


def main() -> int:
    from app.artifacts.contracts import Artifact, ArtifactStatus
    from app.artifacts.files import ARTIFACT_AREA, digest_of
    from app.artifacts.postgres import record_from_artifact
    from app.composition import get_settings, get_workspace
    from app.db.records import ArtifactRecord
    from app.db.session import Database

    apply = "--apply" in sys.argv[1:]
    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL is required to record artifacts.")
        return 1

    area = get_workspace(settings).root / ARTIFACT_AREA
    if not area.is_dir():
        print(f"No artifact area at {area}; nothing to do.")
        return 0

    recoverable = _recoverable(area)
    if not recoverable:
        print(f"No artifacts in the pre-record layout under {area}.")
        return 0

    async def record() -> tuple[int, int]:
        """Insert the missing rows, keeping the engine on one event loop."""

        database = Database(settings.database_url)
        recorded = skipped = 0
        try:
            async with database.session() as session:
                for run_id, artifact_id, filename, path in recoverable:
                    if await session.get(ArtifactRecord, artifact_id) is not None:
                        skipped += 1
                        continue
                    written = digest_of(path)
                    artifact = Artifact(
                        id=artifact_id, name=filename,
                        # The file stays where it is, so the key describes the
                        # layout it was written in, not the current one.
                        relative_path=path.relative_to(area.parent).as_posix(),
                        artifact_type="file",
                        media_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
                        size=written.size, sha256=written.sha256,
                        status=ArtifactStatus.READY, run_id=run_id,
                        created_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
                        metadata={"recovered_from": "pre_record_layout"},
                    )
                    print(f"  {artifact_id}  {run_id}  {filename}  ({written.size:,} bytes)")
                    if apply:
                        session.add(record_from_artifact(artifact))
                    recorded += 1
                if apply:
                    await session.commit()
        finally:
            await database.dispose()
        return recorded, skipped

    recorded, skipped = asyncio.run(record())

    verb = "Recorded" if apply else "Would record"
    print(f"{verb} {recorded} artifact(s); {skipped} already had a record.")
    if not apply:
        print("Nothing was written. Re-run with --apply to record them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
