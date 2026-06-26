import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { MANAGER_ROLES, hasRole } from '../utils/roles.js'

export default function Leaves() {
  const { user } = useAuth()
  const [rows, setRows] = useState([])
  const [employees, setEmployees] = useState([])
  const [types, setTypes] = useState([])
  const [balances, setBalances] = useState([])
  const [form, setForm] = useState({ employee: '', leave_type: '', start_date: '', end_date: '', total_days: '', reason: '' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const normalize = data => data.results || data
  const canApprove = hasRole(user, MANAGER_ROLES)

  const load = async () => {
    const [leaveRes, empRes, typeRes, balanceRes] = await Promise.all([
      api.get('/leave-requests/'),
      api.get('/employees/'),
      api.get('/leave-types/'),
      api.get('/reports/leave-balances/').catch(() => ({ data: { results: [] } }))
    ])
    setRows(normalize(leaveRes.data))
    setEmployees(normalize(empRes.data))
    setTypes(normalize(typeRes.data))
    setBalances(balanceRes.data.results || [])
  }

  useEffect(() => { load().catch(() => {}) }, [])

  const submit = async (e) => {
    e.preventDefault()
    setMessage('')
    setError('')
    try {
      await api.post('/leave-requests/', form)
      setForm({ employee: '', leave_type: '', start_date: '', end_date: '', total_days: '', reason: '' })
      setMessage('Leave request submitted successfully.')
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to submit leave request'))
    }
  }

  const updateStatus = async (row, status) => {
    setMessage('')
    setError('')
    try {
      await api.patch(`/leave-requests/${row.id}/`, { status })
      setMessage(`Leave ${status.toLowerCase()} successfully.`)
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to update leave status'))
    }
  }

  return (
    <section>
      <PageHeader title="Leaves" subtitle="Apply, approve, reject, and automatically deduct leave balances." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <form className="inlineForm" onSubmit={submit}>
        <select value={form.employee} onChange={e => setForm({ ...form, employee: e.target.value })} required>
          <option value="">Employee</option>
          {employees.map(e => <option key={e.id} value={e.id}>{e.full_name}</option>)}
        </select>
        <select value={form.leave_type} onChange={e => setForm({ ...form, leave_type: e.target.value })} required>
          <option value="">Leave type</option>
          {types.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <input type="date" value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} required />
        <input type="date" value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })} required />
        <input type="number" step="0.5" placeholder="Days" value={form.total_days} onChange={e => setForm({ ...form, total_days: e.target.value })} required />
        <input placeholder="Reason" value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} required />
        <button>Apply</button>
      </form>

      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'leave_type_name', label: 'Type' },
        { key: 'start_date', label: 'Start' },
        { key: 'end_date', label: 'End' },
        { key: 'total_days', label: 'Days' },
        { key: 'status', label: 'Status' },
        { key: 'actions', label: 'Actions', render: row => canApprove && row.status === 'PENDING' ? (
          <div className="actions">
            <button onClick={() => updateStatus(row, 'APPROVED')}>Approve</button>
            <button className="dangerBtn" onClick={() => updateStatus(row, 'REJECTED')}>Reject</button>
          </div>
        ) : '-' }
      ]} rows={rows} />

      <PageHeader title="Leave Balances" subtitle="Used days update when leave requests are approved." />
      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'leave_type', label: 'Leave Type' },
        { key: 'allocated', label: 'Allocated' },
        { key: 'used', label: 'Used' },
        { key: 'remaining', label: 'Remaining' }
      ]} rows={balances.map((row, index) => ({ ...row, id: `${row.employee_id}-${row.leave_type}-${index}` }))} />
    </section>
  )
}
