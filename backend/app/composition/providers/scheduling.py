"""Scheduled saved-report execution."""

from app.composition.lifecycle import provider
from app.composition.providers.artifacts import get_artifact_store
from app.composition.providers.delivery import get_delivery_service
from app.composition.providers.environment import get_workspace
from app.composition.providers.orchestration import get_report_rerun_service, get_report_template_registry
from app.composition.providers.persistence import get_runtime_database, get_saved_report_store
from app.composition.providers.settings import get_settings
from app.reports.execution import SavedReportExecutionService
from app.scheduling.store import PostgresScheduledReportStore, ScheduledReportStore
from app.scheduling.worker import SchedulerWorker


@provider
def get_scheduled_report_store() -> ScheduledReportStore:
    """Use the existing runtime PostgreSQL database for scheduled reports."""

    return PostgresScheduledReportStore(get_runtime_database())


@provider
def get_scheduler_worker() -> SchedulerWorker:
    """Return the worker a scheduling process runs on a fixed interval."""

    from datetime import timedelta

    settings = get_settings()
    execution_service = SavedReportExecutionService(
        templates=get_report_template_registry(), reruns=get_report_rerun_service(),
        workspace=get_workspace(settings), artifacts=get_artifact_store(),
    )
    return SchedulerWorker(
        schedules=get_scheduled_report_store(), saved_reports=get_saved_report_store(),
        execution_service=execution_service, delivery=get_delivery_service(),
        stale_claim_after=timedelta(seconds=settings.worker_claim_stale_seconds),
    )
