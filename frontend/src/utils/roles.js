export const ROLES = {
  OWNER: 'OWNER',
  ADMIN: 'ADMIN',
  HR: 'HR',
  MANAGER: 'MANAGER',
  EMPLOYEE: 'EMPLOYEE',
  PAYROLL: 'PAYROLL',
  IT: 'IT',
  VIEWER: 'VIEWER'
}

export const ROLE_LABELS = {
  OWNER: 'Owner',
  ADMIN: 'Admin',
  HR: 'HR',
  MANAGER: 'Manager',
  EMPLOYEE: 'Employee',
  PAYROLL: 'Payroll',
  IT: 'IT / Asset Manager',
  VIEWER: 'Viewer'
}

export const MANAGEMENT_ROLES = [ROLES.OWNER, ROLES.ADMIN]
export const HR_ROLES = [ROLES.OWNER, ROLES.ADMIN, ROLES.HR]
export const PAYROLL_ROLES = [ROLES.OWNER, ROLES.ADMIN, ROLES.PAYROLL]
export const ASSET_ROLES = [ROLES.OWNER, ROLES.ADMIN, ROLES.HR, ROLES.IT]
export const MANAGER_ROLES = [ROLES.OWNER, ROLES.ADMIN, ROLES.HR, ROLES.MANAGER]
export const RECRUITMENT_ROLES = [ROLES.OWNER, ROLES.ADMIN, ROLES.HR, ROLES.MANAGER]
export const HELPDESK_ROLES = [ROLES.OWNER, ROLES.ADMIN, ROLES.HR, ROLES.IT]

export function hasRole(user, roles) {
  return Boolean(user?.role && roles.includes(user.role))
}

export function canManageHR(user) {
  return hasRole(user, HR_ROLES)
}

export function canManagePayroll(user) {
  return hasRole(user, PAYROLL_ROLES)
}

export function canManageAssets(user) {
  return hasRole(user, ASSET_ROLES)
}

export function canManageOrganization(user) {
  return hasRole(user, MANAGEMENT_ROLES)
}
