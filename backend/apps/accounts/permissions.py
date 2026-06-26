from rest_framework.permissions import BasePermission
from .models import Membership


MANAGEMENT_ROLES = {Membership.ROLE_OWNER, Membership.ROLE_ADMIN}
HR_ROLES = {Membership.ROLE_OWNER, Membership.ROLE_ADMIN, Membership.ROLE_HR}
PAYROLL_ROLES = {Membership.ROLE_OWNER, Membership.ROLE_ADMIN, Membership.ROLE_PAYROLL}
IT_ROLES = {Membership.ROLE_OWNER, Membership.ROLE_ADMIN, Membership.ROLE_IT}
ASSET_ROLES = {Membership.ROLE_OWNER, Membership.ROLE_ADMIN, Membership.ROLE_HR, Membership.ROLE_IT}
MANAGER_ROLES = {Membership.ROLE_OWNER, Membership.ROLE_ADMIN, Membership.ROLE_HR, Membership.ROLE_MANAGER}


def get_role(user):
    if not user.is_authenticated or not user.current_organization_id:
        return None
    membership = user.memberships.filter(organization=user.current_organization, is_active=True).first()
    return membership.role if membership else None


class IsOrganizationMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.current_organization_id and get_role(request.user))


class IsOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) in MANAGEMENT_ROLES


class IsHR(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) in HR_ROLES


class IsPayroll(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) in PAYROLL_ROLES


class IsManagerLevel(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) in MANAGER_ROLES


class IsITOrAssetAdmin(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) in ASSET_ROLES
