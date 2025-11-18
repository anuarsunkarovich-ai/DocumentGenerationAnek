"""Celery application wiring for document-generation workers."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

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
)
