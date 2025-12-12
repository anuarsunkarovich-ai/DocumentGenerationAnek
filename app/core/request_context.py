"""Request and job context helpers for logs, metrics, and tracing."""

from contextvars import ContextVar
from uuid import UUID

from fastapi import Request

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_job_id: ContextVar[str | None] = ContextVar("job_id", default=None)
_organization_id: ContextVar[str | None] = ContextVar("organization_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)
_template_version_id: ContextVar[str | None] = ContextVar("template_version_id", default=None)

_CONTEXT_VARS = {
    "request_id": _request_id,
    "correlation_id": _correlation_id,
    "job_id": _job_id,
    "organization_id": _organization_id,
    "user_id": _user_id,
    "template_version_id": _template_version_id,
}


def _normalize(value: str | UUID | None) -> str | None:
    """Normalize UUID values for log and trace serialization."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    return value


def bind_context(
    *,
    request_id: str | None = None,
    correlation_id: str | None = None,
    job_id: UUID | str | None = None,
    organization_id: UUID | str | None = None,
    user_id: UUID | str | None = None,
    template_version_id: UUID | str | None = None,
) -> None:
    """Bind one or more fields into the current request/task context."""
    values = {
        "request_id": request_id,
        "correlation_id": correlation_id,
        "job_id": job_id,
        "organization_id": organization_id,
        "user_id": user_id,
        "template_version_id": template_version_id,
    }
    for key, value in values.items():
        if value is not None:
            _CONTEXT_VARS[key].set(_normalize(value))


def bind_request_state(
    request: Request,
    *,
    user_id: UUID | str | None = None,
    organization_id: UUID | str | None = None,
    template_version_id: UUID | str | None = None,
    job_id: UUID | str | None = None,
) -> None:
    """Mirror selected context fields onto request state for downstream handlers."""
    bind_context(
        user_id=user_id,
        organization_id=organization_id,
        template_version_id=template_version_id,
        job_id=job_id,
    )
    if user_id is not None:
        request.state.user_id = _normalize(user_id)
    if organization_id is not None:
        request.state.organization_id = _normalize(organization_id)
    if template_version_id is not None:
        request.state.template_version_id = _normalize(template_version_id)
    if job_id is not None:
        request.state.job_id = _normalize(job_id)


def clear_context() -> None:
    """Reset all bound context fields for the current task."""
    for variable in _CONTEXT_VARS.values():
        variable.set(None)


def get_context() -> dict[str, str | None]:
    """Return the current observability context as a serializable mapping."""
    return {
        "request_id": _request_id.get(),
        "correlation_id": _correlation_id.get(),
        "job_id": _job_id.get(),
        "organization_id": _organization_id.get(),
        "user_id": _user_id.get(),
        "template_version_id": _template_version_id.get(),
    }


def get_request_id() -> str | None:
    """Return the current request identifier."""
    return _request_id.get()


def get_correlation_id() -> str | None:
    """Return the current correlation identifier."""
    return _correlation_id.get()
