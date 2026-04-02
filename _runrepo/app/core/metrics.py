"""Prometheus metrics for API, worker, and storage observability."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_LATENCY_SECONDS = Histogram(
    "http_request_latency_seconds",
    "HTTP request latency by method, route, and status code.",
    labelnames=("method", "route", "status_code"),
)
REQUEST_COUNT = Counter(
    "http_requests_total",
    "HTTP request count by method, route, and status code.",
    labelnames=("method", "route", "status_code"),
)
JOB_DURATION_SECONDS = Histogram(
    "document_job_duration_seconds",
    "Document generation duration by outcome.",
    labelnames=("result",),
)
GENERATION_RESULT_COUNT = Counter(
    "document_job_result_total",
    "Document generation outcomes.",
    labelnames=("result",),
)
CACHE_EVENT_COUNT = Counter(
    "document_generation_cache_total",
    "Document generation cache outcomes.",
    labelnames=("result",),
)
STORAGE_ERROR_COUNT = Counter(
    "storage_errors_total",
    "Storage-layer errors by operation.",
    labelnames=("operation",),
)
QUEUE_DEPTH = Gauge(
    "document_generation_queue_depth",
    "Current Redis queue depth for document generation tasks.",
)
WORKER_UP = Gauge(
    "document_generation_worker_up",
    "Worker availability by worker hostname.",
    labelnames=("worker",),
)


def record_request_metrics(*, method: str, route: str, status_code: int, duration_seconds: float) -> None:
    """Record HTTP request latency and volume."""
    labels = {
        "method": method,
        "route": route,
        "status_code": str(status_code),
    }
    REQUEST_COUNT.labels(**labels).inc()
    REQUEST_LATENCY_SECONDS.labels(**labels).observe(duration_seconds)


def record_job_result(*, result: str, duration_seconds: float | None = None) -> None:
    """Record one document-generation outcome and optional duration."""
    GENERATION_RESULT_COUNT.labels(result=result).inc()
    if duration_seconds is not None:
        JOB_DURATION_SECONDS.labels(result=result).observe(duration_seconds)


def record_cache_event(*, hit: bool) -> None:
    """Track cache hits and misses for generation requests."""
    CACHE_EVENT_COUNT.labels(result="hit" if hit else "miss").inc()


def record_storage_error(*, operation: str) -> None:
    """Track storage failures."""
    STORAGE_ERROR_COUNT.labels(operation=operation).inc()


def observe_queue_depth(*, depth: int) -> None:
    """Publish the current queue depth."""
    QUEUE_DEPTH.set(depth)


def observe_worker_status(*, workers: dict[str, bool]) -> None:
    """Publish worker availability gauges."""
    WORKER_UP.clear()
    for worker_name, is_up in workers.items():
        WORKER_UP.labels(worker=worker_name).set(1 if is_up else 0)


def render_metrics() -> tuple[bytes, str]:
    """Render the current Prometheus payload."""
    return generate_latest(), CONTENT_TYPE_LATEST
