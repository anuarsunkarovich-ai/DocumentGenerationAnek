"""Authorization policy helpers for tenant-scoped routes."""

from app.api.dependencies.auth import CurrentMembership, resolve_membership
from app.core.exceptions import AuthorizationError
from app.models.enums import UserRole
from app.models.user import User

_TEMPLATE_READ_ROLES = {
    UserRole.VIEWER,
    UserRole.OPERATOR,
    UserRole.MANAGER,
    UserRole.ADMIN,
}
_TEMPLATE_WRITE_ROLES = {
    UserRole.MANAGER,
    UserRole.ADMIN,
}
_GENERATION_ROLES = {
    UserRole.OPERATOR,
    UserRole.MANAGER,
    UserRole.ADMIN,
}
_AUDIT_ROLES = {
    UserRole.ADMIN,
}


def require_template_read_access(
    user: User,
    organization_id=None,
) -> CurrentMembership:
    """Ensure the user can read template and job data for one organization."""
    membership = resolve_membership(user=user, organization_id=organization_id)
    if membership.role not in _TEMPLATE_READ_ROLES:
        raise AuthorizationError("User does not have permission to read templates.")
    return membership


def require_job_read_access(
    user: User,
    organization_id=None,
) -> CurrentMembership:
    """Ensure the user can read job status and artifacts for one organization."""
    membership = resolve_membership(user=user, organization_id=organization_id)
    if membership.role not in _TEMPLATE_READ_ROLES:
        raise AuthorizationError("User does not have permission to read document jobs.")
    return membership


def require_template_write_access(
    user: User,
    organization_id=None,
) -> CurrentMembership:
    """Ensure the user can upload or modify templates for one organization."""
    membership = resolve_membership(user=user, organization_id=organization_id)
    if membership.role not in _TEMPLATE_WRITE_ROLES:
        raise AuthorizationError("User does not have permission to modify templates.")
    return membership


def require_generation_access(
    user: User,
    organization_id=None,
) -> CurrentMembership:
    """Ensure the user can generate documents for one organization."""
    membership = resolve_membership(user=user, organization_id=organization_id)
    if membership.role not in _GENERATION_ROLES:
        raise AuthorizationError("User does not have permission to generate documents.")
    return membership


def require_audit_access(
    user: User,
    organization_id=None,
) -> CurrentMembership:
    """Ensure the user can access audit data for one organization."""
    membership = resolve_membership(user=user, organization_id=organization_id)
    if membership.role not in _AUDIT_ROLES:
        raise AuthorizationError("User does not have permission to access audit logs.")
    return membership
