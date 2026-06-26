import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { ROLE_LABELS } from '../utils/roles.js'

const initialForm = {
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  role: 'EMPLOYEE',
  employee_code: '',
  department: '',
  designation: '',
  manager: '',
  phone: '',
  date_of_joining: '',
  employment_type: 'FULL_TIME',
  status: 'ACTIVE',
  salary_basic: ''
}

export default function Employees() {
  const [rows, setRows] = useState([])
  const [departments, setDepartments] = useState([])
  const [form, setForm] = useState(initialForm)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [passwords, setPasswords] = useState({})

  const normalize = (data) => data.results || data

  const load = async () => {
    const [employeeRes, departmentRes] = await Promise.all([
      api.get('/employees/'),
      api.get('/departments/')
    ])
    setRows(normalize(employeeRes.data))
    setDepartments(normalize(departmentRes.data))
  }

  useEffect(() => { load().catch(() => {}) }, [])

  const updateForm = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  const getPayload = () => {
    const payload = { ...form }
    if (!payload.department) payload.department = null
    if (!payload.manager) payload.manager = null
    if (!payload.salary_basic) payload.salary_basic = 0
    if (!payload.date_of_joining) payload.date_of_joining = null
    return payload
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.post('/employees/', getPayload())
      setForm(initialForm)
      setMessage('Employee profile and login access created. Share the email and password manually with the employee.')
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to create employee'))
    }
  }

  const resetPassword = async (employeeId) => {
    const password = passwords[employeeId]
    if (!password) {
      setError('Enter a new password before resetting.')
      return
    }
    setError('')
    setMessage('')
    try {
      await api.post(`/employees/${employeeId}/set-password/`, { password })
      setPasswords(prev => ({ ...prev, [employeeId]: '' }))
      setMessage('Employee password updated successfully.')
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to reset password'))
    }
  }

  const toggleLogin = async (employee) => {
    setError('')
    setMessage('')
    try {
      const action = employee.login_enabled ? 'disable-login' : 'enable-login'
      await api.post(`/employees/${employee.id}/${action}/`)
      setMessage(employee.login_enabled ? 'Employee login disabled.' : 'Employee login enabled.')
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to update login status'))
    }
  }

  return (
    <section>
      <PageHeader title="Employees" subtitle="Create employees directly with role and login access. No invite flow required." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      <form className="inlineForm wideForm" onSubmit={submit}>
        <input placeholder="Email" value={form.email} onChange={e => updateForm('email', e.target.value)} required />
        <input placeholder="First name" value={form.first_name} onChange={e => updateForm('first_name', e.target.value)} />
        <input placeholder="Last name" value={form.last_name} onChange={e => updateForm('last_name', e.target.value)} />
        <input type="password" placeholder="Login password" value={form.password} onChange={e => updateForm('password', e.target.value)} />
        <select value={form.role} onChange={e => updateForm('role', e.target.value)}>
          {Object.entries(ROLE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <input placeholder="Employee code" value={form.employee_code} onChange={e => updateForm('employee_code', e.target.value)} required />
        <select value={form.department} onChange={e => updateForm('department', e.target.value)}>
          <option value="">Department</option>
          {departments.map(dept => <option key={dept.id} value={dept.id}>{dept.name}</option>)}
        </select>
        <input placeholder="Designation" value={form.designation} onChange={e => updateForm('designation', e.target.value)} />
        <select value={form.manager} onChange={e => updateForm('manager', e.target.value)}>
          <option value="">Reporting manager</option>
          {rows.map(emp => <option key={emp.id} value={emp.id}>{emp.full_name}</option>)}
        </select>
        <input placeholder="Phone" value={form.phone} onChange={e => updateForm('phone', e.target.value)} />
        <input type="date" value={form.date_of_joining} onChange={e => updateForm('date_of_joining', e.target.value)} />
        <select value={form.employment_type} onChange={e => updateForm('employment_type', e.target.value)}>
          <option value="FULL_TIME">Full Time</option>
          <option value="PART_TIME">Part Time</option>
          <option value="CONTRACT">Contract</option>
          <option value="INTERN">Intern</option>
        </select>
        <select value={form.status} onChange={e => updateForm('status', e.target.value)}>
          <option value="ACTIVE">Active</option>
          <option value="PROBATION">Probation</option>
          <option value="NOTICE">Notice</option>
          <option value="EXITED">Exited</option>
        </select>
        <input placeholder="Basic salary" value={form.salary_basic} onChange={e => updateForm('salary_basic', e.target.value)} />
        <button>Create Employee</button>
      </form>
      <DataTable columns={[
        { key: 'employee_code', label: 'Code' },
        { key: 'full_name', label: 'Name' },
        { key: 'user_email', label: 'Email' },
        { key: 'department_name', label: 'Department' },
        { key: 'designation', label: 'Designation' },
        { key: 'account_role', label: 'Role' },
        { key: 'login_enabled', label: 'Login', render: row => row.login_enabled ? 'Enabled' : 'Disabled' },
        {
          key: 'password_action',
          label: 'Reset Password',
          render: row => (
            <div className="miniAction">
              <input
                type="password"
                placeholder="New password"
                value={passwords[row.id] || ''}
                onChange={e => setPasswords(prev => ({ ...prev, [row.id]: e.target.value }))}
              />
              <button type="button" onClick={() => resetPassword(row.id)}>Set</button>
            </div>
          )
        },
        {
          key: 'login_action',
          label: 'Access',
          render: row => <button type="button" onClick={() => toggleLogin(row)}>{row.login_enabled ? 'Disable' : 'Enable'}</button>
        }
      ]} rows={rows} />
    </section>
  )
}
