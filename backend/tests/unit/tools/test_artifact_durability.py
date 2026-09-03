"""What every artifact registry must guarantee, whatever holds its records.

The in-process and PostgreSQL registries share one write sequence and differ
only in where the record lives, so the rules that matter — a record never
outlives a failed write, a key never escapes the artifact area, one run never
sees another's files — are asserted against the contract rather than against
one implementation. ``tests/integration/test_postgres_artifacts.py`` runs the
durability half of this against a real database.
"""

import uuid
from pathlib import Path

import pytest

from app.artifacts.contracts import ArtifactStatus
from app.artifacts.files import WorkspaceArtifactFiles, digest_of, storage_key
from app.artifacts.postgres import PostgresArtifactStore
from app.artifacts.store import WorkspaceArtifactStore
from app.config import Settings
from app.environment.workspace import Workspace

WORKSPACE_ID = uuid.uuid4()


class FailingFiles(WorkspaceArtifactFiles):
    """Accept the source, then fail while writing the bytes.

    Reproduces the case the two-step record exists for: validation passed, the
    record was created, and the copy died part way through.
    """

    def write(self, key: str, source: Path) -> None:
        raise OSError("disk full")


def _store(root: Path, **overrides: object) -> WorkspaceArtifactStore:
    return WorkspaceArtifactStore(Workspace(root), **overrides)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_a_registered_artifact_records_the_bytes_that_landed(tmp_path: Path) -> None:
    (tmp_path / "report.md").write_text("# Report\n")
    store = _store(tmp_path)

    artifact = await store.register(workspace_id=WORKSPACE_ID, run_id="run-one", source_path="report.md")
    path = await store.path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact.id)

    assert artifact.status is ArtifactStatus.READY
    assert path is not None
    written = digest_of(path)
    assert (artifact.size, artifact.sha256) == (written.size, written.sha256)
    assert artifact.size == len("# Report\n")


@pytest.mark.asyncio
async def test_a_failed_write_leaves_no_retrievable_record(tmp_path: Path) -> None:
    (tmp_path / "report.md").write_text("# Report\n")
    workspace = Workspace(tmp_path)
    store = WorkspaceArtifactStore(
        workspace, files=FailingFiles(workspace, max_artifact_bytes=65_536)
    )

    with pytest.raises(ValueError, match="could not be written"):
        await store.register(workspace_id=WORKSPACE_ID, run_id="run-one", source_path="report.md")

    # The row survives so the failure is visible, but nothing hands it out.
    assert await store.list(workspace_id=WORKSPACE_ID, run_id="run-one") == []


@pytest.mark.asyncio
async def test_a_record_whose_file_vanished_resolves_to_no_path(tmp_path: Path) -> None:
    """A download must fail rather than succeed against a hole on disk."""

    (tmp_path / "report.md").write_text("# Report\n")
    store = _store(tmp_path)
    artifact = await store.register(workspace_id=WORKSPACE_ID, run_id="run-one", source_path="report.md")

    path = await store.path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact.id)
    assert path is not None
    path.unlink()

    # The record is still ready — the bytes are what went missing.
    assert await store.get(workspace_id=WORKSPACE_ID, artifact_id=artifact.id) is not None
    assert await store.path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact.id) is None


@pytest.mark.asyncio
async def test_one_run_never_resolves_another_runs_artifacts(tmp_path: Path) -> None:
    (tmp_path / "one.txt").write_text("one")
    (tmp_path / "two.txt").write_text("two")
    store = _store(tmp_path)

    first = await store.register(workspace_id=WORKSPACE_ID, run_id="first", source_path="one.txt")
    second = await store.register(workspace_id=WORKSPACE_ID, run_id="second", source_path="two.txt")

    assert [item.id for item in await store.list(workspace_id=WORKSPACE_ID, run_id="first")] == [first.id]
    assert [item.id for item in await store.list(workspace_id=WORKSPACE_ID, run_id="second")] == [second.id]
    assert first.relative_path.startswith("artifacts/first/")
    assert second.relative_path.startswith("artifacts/second/")


@pytest.mark.asyncio
async def test_a_run_identifier_cannot_escape_the_artifact_area(tmp_path: Path) -> None:
    (tmp_path / "one.txt").write_text("one")
    store = _store(tmp_path)

    for hostile in ("../escape", "a/b", "..", ""):
        with pytest.raises(ValueError):
            await store.register(workspace_id=WORKSPACE_ID, run_id=hostile, source_path="one.txt")


def test_a_storage_key_is_provider_independent(tmp_path: Path) -> None:
    """Nothing machine-specific may reach a record, so a key must resolve elsewhere."""

    key = storage_key(run_id="run-one", artifact_id="abc", filename="report.pdf")

    assert key == "artifacts/run-one/abc/report.pdf"
    assert not Path(key).is_absolute()
    assert str(tmp_path) not in key


@pytest.mark.asyncio
async def test_an_unresolvable_identifier_is_refused_rather_than_searched(tmp_path: Path) -> None:
    store = _store(tmp_path)

    assert await store.get(workspace_id=WORKSPACE_ID, artifact_id="../../etc/passwd") is None
    assert await store.path_for(workspace_id=WORKSPACE_ID, artifact_id="not-a-uuid") is None


def test_files_written_before_records_existed_are_recoverable(tmp_path: Path) -> None:
    """The pre-record layout keeps both identifiers in the path, so a row can be rebuilt."""

    from scripts.backfill_artifacts import _recoverable

    area = tmp_path / "artifacts"
    (area / "run-one").mkdir(parents=True)
    (area / "run-one" / "03a0930b-adbd-4db3-9e63-e53c02a81023-monthly_business_review.pdf").write_bytes(b"pdf")
    # A hyphenated filename must not confuse the split.
    (area / "run-one" / "8916f1ca-47ed-4329-82f2-5f4574d8d963-a-b-c.docx").write_bytes(b"docx")
    # Already recorded by a store that used the current layout.
    (area / "run-two" / "f834383d-9bd8-4e3f-bf1d-9590f4b601c4").mkdir(parents=True)
    (area / "run-two" / "f834383d-9bd8-4e3f-bf1d-9590f4b601c4" / "report.pdf").write_bytes(b"pdf")
    # Not something this registry issued.
    (area / "run-one" / "stray.txt").write_bytes(b"stray")

    found = [(run_id, artifact_id, filename) for run_id, artifact_id, filename, _ in _recoverable(area)]

    assert found == [
        ("run-one", "03a0930b-adbd-4db3-9e63-e53c02a81023", "monthly_business_review.pdf"),
        ("run-one", "8916f1ca-47ed-4329-82f2-5f4574d8d963", "a-b-c.docx"),
    ]


def test_a_recovered_key_still_resolves_inside_the_artifact_area(tmp_path: Path) -> None:
    """A backfilled record points at the file where it already sits."""

    files = WorkspaceArtifactFiles(Workspace(tmp_path), max_artifact_bytes=65_536)
    legacy = tmp_path / "artifacts" / "run-one"
    legacy.mkdir(parents=True)
    (legacy / "abc-report.pdf").write_bytes(b"pdf")

    assert files.path("artifacts/run-one/abc-report.pdf") is not None
    # Containment still holds for a key that did not come from storage_key().
    assert files.path("../../etc/passwd") is None


def test_the_durable_artifact_backend_requires_a_database_url() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL is required"):
        # Do not inherit a developer's local `.env` database URL in this missing-value test.
        Settings(artifact_backend="postgres", database_url="")

    settings = Settings(
        artifact_backend="postgres", database_url="postgresql+asyncpg://user:password@db/agent"
    )

    assert settings.artifact_backend == "postgres"


def test_the_default_artifact_backend_keeps_records_in_process() -> None:
    """The durable backend is opt-in, so an unconfigured deployment is unchanged."""

    assert Settings(_env_file=None).artifact_backend == "in_memory"


def test_the_configured_backend_selects_the_matching_store(monkeypatch) -> None:
    from app.composition.providers import artifacts as provider_module

    monkeypatch.setattr(
        provider_module, "get_settings",
        lambda: Settings(_env_file=None, agent_workspace_root="./var",
                         artifact_backend="postgres",
                         database_url="postgresql+asyncpg://user:password@db/agent"),
    )
    built: list[object] = []
    monkeypatch.setattr(provider_module, "get_runtime_database", lambda: built.append("db") or None)

    provider_module.get_artifact_store.cache_clear()
    try:
        store = provider_module.get_artifact_store()
    finally:
        provider_module.get_artifact_store.cache_clear()

    assert isinstance(store, PostgresArtifactStore)
    assert built == ["db"]
