import React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import RoleRoute from './components/RoleRoute.jsx'
import DashboardLayout from './layouts/DashboardLayout.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Employees from './pages/Employees.jsx'
import Departments from './pages/Departments.jsx'
import Attendance from './pages/Attendance.jsx'
import Shifts from './pages/Shifts.jsx'
import Holidays from './pages/Holidays.jsx'
import Leaves from './pages/Leaves.jsx'
import Payroll from './pages/Payroll.jsx'
import Documents from './pages/Documents.jsx'
import Reports from './pages/Reports.jsx'
import Profile from './pages/Profile.jsx'
import Expenses from './pages/Expenses.jsx'
import Notifications from './pages/Notifications.jsx'
import Announcements from './pages/Announcements.jsx'
import Policies from './pages/Policies.jsx'
import Performance from './pages/Performance.jsx'
import Assets from './pages/Assets.jsx'
import Offboarding from './pages/Offboarding.jsx'
import Recruitment from './pages/Recruitment.jsx'
import Training from './pages/Training.jsx'
import Helpdesk from './pages/Helpdesk.jsx'
import Timesheets from './pages/Timesheets.jsx'
import Letters from './pages/Letters.jsx'
import Settings from './pages/Settings.jsx'
import { HR_ROLES, PAYROLL_ROLES, MANAGEMENT_ROLES, RECRUITMENT_ROLES } from './utils/roles.js'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route element={<RoleRoute roles={HR_ROLES} />}>
            <Route path="/employees" element={<Employees />} />
            <Route path="/departments" element={<Departments />} />
            <Route path="/shifts" element={<Shifts />} />
            <Route path="/holidays" element={<Holidays />} />
            <Route path="/documents" element={<Documents />} />
          </Route>
          <Route path="/profile" element={<Profile />} />
          <Route path="/attendance" element={<Attendance />} />
          <Route path="/leaves" element={<Leaves />} />
          <Route path="/expenses" element={<Expenses />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/announcements" element={<Announcements />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/performance" element={<Performance />} />
          <Route path="/training" element={<Training />} />
          <Route path="/helpdesk" element={<Helpdesk />} />
          <Route path="/timesheets" element={<Timesheets />} />
          <Route path="/letters" element={<Letters />} />
          <Route path="/assets" element={<Assets />} />
          <Route element={<RoleRoute roles={RECRUITMENT_ROLES} />}>
            <Route path="/recruitment" element={<Recruitment />} />
          </Route>
          <Route path="/offboarding" element={<Offboarding />} />
          <Route path="/reports" element={<Reports />} />
          <Route element={<RoleRoute roles={PAYROLL_ROLES} />}>
            <Route path="/payroll" element={<Payroll />} />
          </Route>
          <Route element={<RoleRoute roles={MANAGEMENT_ROLES} />}>
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}
