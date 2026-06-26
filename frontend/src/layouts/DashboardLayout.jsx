import React from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { HR_ROLES, PAYROLL_ROLES, MANAGEMENT_ROLES, RECRUITMENT_ROLES, hasRole } from '../utils/roles.js'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/profile', label: 'My Profile' },
  { to: '/employees', label: 'Employees', roles: HR_ROLES },
  { to: '/departments', label: 'Departments', roles: HR_ROLES },
  { to: '/attendance', label: 'Attendance' },
  { to: '/shifts', label: 'Shifts', roles: HR_ROLES },
  { to: '/holidays', label: 'Holidays', roles: HR_ROLES },
  { to: '/leaves', label: 'Leaves' },
  { to: '/expenses', label: 'Expenses' },
  { to: '/notifications', label: 'Notifications' },
  { to: '/announcements', label: 'Announcements' },
  { to: '/policies', label: 'Policies' },
  { to: '/performance', label: 'Performance' },
  { to: '/training', label: 'Training / LMS' },
  { to: '/helpdesk', label: 'Helpdesk' },
  { to: '/timesheets', label: 'Timesheets' },
  { to: '/letters', label: 'HR Letters' },
  { to: '/recruitment', label: 'Recruitment', roles: RECRUITMENT_ROLES },
  { to: '/assets', label: 'Assets' },
  { to: '/offboarding', label: 'Offboarding' },
  { to: '/reports', label: 'Reports' },
  { to: '/payroll', label: 'Payroll', roles: PAYROLL_ROLES },
  { to: '/documents', label: 'Documents', roles: HR_ROLES },
  { to: '/settings', label: 'Settings', roles: MANAGEMENT_ROLES }
]

export default function DashboardLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const visibleLinks = links.filter(link => !link.roles || hasRole(user, link.roles))

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brand">EmployeeHub</div>
        <div className="orgName">{user?.organization?.name}</div>
        <nav>
          {visibleLinks.map(link => <NavLink key={link.to} to={link.to}>{link.label}</NavLink>)}
        </nav>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            <h2>{user?.first_name || user?.email}</h2>
            <p>{user?.role}</p>
          </div>
          <button onClick={handleLogout}>Logout</button>
        </header>
        <Outlet />
      </main>
    </div>
  )
}
