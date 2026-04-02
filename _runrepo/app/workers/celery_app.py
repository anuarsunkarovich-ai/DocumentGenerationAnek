"""Celery application wiring for document-generation workers."""

from celery import Celery

from app.core.config import get_settings
from app.core.error_reporting import configure_error_reporting

settings = get_settings()
configure_error_reporting(runtime="worker")

celery_app = Celery(
    "lean_generator_backend",
    broker=settings.redis.broker_url,
    backend=settings.redis.result_backend_url,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_default_queue=settings.worker.queue_name,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=settings.worker.result_expires_seconds,
    beat_schedule={
        "recover-stale-document-jobs": {
            "task": "document_jobs.recover_stale",
            "schedule": settings.worker.stale_job_timeout_seconds,
        },
        "cleanup-retention-data": {
            "task": "maintenance.cleanup",
            "schedule": settings.worker.maintenance_cleanup_interval_minutes * 60,
        },
        "run-billing-cycle": {
            "task": "billing.run_cycle",
            "schedule": settings.worker.billing_cycle_interval_minutes * 60,
        },
    },
)
