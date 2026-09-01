"""PostgreSQL-backed artifact records, so download links outlive the process."""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.artifacts.contracts import Artifact, ArtifactStatus
from app.artifacts.files import WorkspaceArtifactFiles
from app.artifacts.store import BaseArtifactStore, validated_artifact_id
from app.db.records import ArtifactRecord
from app.db.session import Database


class PostgresArtifactStore(BaseArtifactStore):
    """Keep the record in PostgreSQL and the bytes with the file provider."""

    def __init__(self, files: WorkspaceArtifactFiles, database: Database) -> None:
        super().__init__(files)
        self._database = database

    async def get(self, artifact_id: str) -> Artifact | None:
        try:
            identifier = validated_artifact_id(artifact_id)
        except ValueError:
            return None
        record = await self._read(identifier)
        if record is None or record.status != ArtifactStatus.READY.value:
            return None
        return artifact_from_record(record)

    async def path_for(self, artifact_id: str) -> Path | None:
        artifact = await self.get(artifact_id)
        return self._files.path(artifact.relative_path) if artifact else None

    async def list(self, *, run_id: str | None = None) -> list[Artifact]:
        statement = select(ArtifactRecord).where(ArtifactRecord.status == ArtifactStatus.READY.value)
        if run_id is not None:
            statement = statement.where(ArtifactRecord.run_id == run_id)
        statement = statement.order_by(ArtifactRecord.created_at.desc(), ArtifactRecord.id.desc())
        try:
            async with self._database.session() as session:
                records = (await session.scalars(statement)).all()
        except SQLAlchemyError as error:
            raise RuntimeError("Artifact storage operation failed") from error
        return [artifact_from_record(record) for record in records]

    async def _record_pending(self, artifact: Artifact) -> None:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    session.add(record_from_artifact(artifact))
        except SQLAlchemyError as error:
            raise RuntimeError("Artifact storage operation failed") from error

    async def _record_ready(self, artifact: Artifact) -> None:
        """Promote the row only once the written bytes have been measured."""

        try:
            async with self._database.session() as session:
                async with session.begin():
                    record = await session.get(ArtifactRecord, artifact.id)
                    if record is None:
                        return
                    record.size, record.sha256 = artifact.size, artifact.sha256
                    record.status = ArtifactStatus.READY.value
        except SQLAlchemyError as error:
            raise RuntimeError("Artifact storage operation failed") from error

    async def _record_failed(self, artifact_id: str) -> None:
        """Mark a row unusable. A failure here must not mask the original one."""

        try:
            async with self._database.session() as session:
                async with session.begin():
                    record = await session.get(ArtifactRecord, artifact_id)
                    if record is not None:
                        record.status = ArtifactStatus.FAILED.value
        except SQLAlchemyError:
            return

    async def _read(self, artifact_id: str) -> ArtifactRecord | None:
        try:
            async with self._database.session() as session:
                return await session.get(ArtifactRecord, artifact_id)
        except SQLAlchemyError as error:
            raise RuntimeError("Artifact storage operation failed") from error


def record_from_artifact(artifact: Artifact) -> ArtifactRecord:
    """Map a contract onto its row. Public so a backfill can write one directly."""

    return ArtifactRecord(
        id=artifact.id, run_id=artifact.run_id, name=artifact.name,
        storage_key=artifact.relative_path, artifact_type=artifact.artifact_type,
        media_type=artifact.media_type, size=artifact.size, sha256=artifact.sha256,
        status=artifact.status.value, output_format=artifact.output_format,
        template_id=artifact.template_id, template_version=artifact.template_version,
        metadata_=dict(artifact.metadata), created_at=artifact.created_at,
        expires_at=artifact.expires_at,
    )


def artifact_from_record(record: ArtifactRecord) -> Artifact:
    return Artifact(
        id=record.id, name=record.name, relative_path=record.storage_key,
        artifact_type=record.artifact_type, media_type=record.media_type, size=record.size,
        sha256=record.sha256, status=ArtifactStatus(record.status), run_id=record.run_id,
        created_at=record.created_at, output_format=record.output_format,
        template_id=record.template_id, template_version=record.template_version,
        expires_at=record.expires_at, metadata=dict(record.metadata_ or {}),
    )
