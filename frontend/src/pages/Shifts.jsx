import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'

const initialShift = {
  name: '',
  start_time: '09:00',
  end_time: '18:00',
  break_minutes: 60,
  grace_minutes: 10,
  half_day_hours: 4,
  full_day_hours: 8,
  overtime_after_minutes: 30,
  weekly_off_days: 'SUN',
  is_default: false,
  is_active: true
}

const initialAssignment = {
  employee: '',
  shift: '',
  start_date: '',
  end_date: '',
  is_active: true
}

export default function Shifts() {
  const [shifts, setShifts] = useState([])
  const [assignments, setAssignments] = useState([])
  const [employees, setEmployees] = useState([])
  const [shiftForm, setShiftForm] = useState(initialShift)
  const [assignmentForm, setAssignmentForm] = useState(initialAssignment)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const normalize = data => data.results || data

  const load = async () => {
    const [shiftRes, assignmentRes, employeeRes] = await Promise.all([
      api.get('/shifts/'),
      api.get('/shift-assignments/'),
      api.get('/employees/')
    ])
    setShifts(normalize(shiftRes.data))
    setAssignments(normalize(assignmentRes.data))
    setEmployees(normalize(employeeRes.data))
  }

  useEffect(() => { load().catch(() => {}) }, [])

  const createShift = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.post('/shifts/', shiftForm)
      setShiftForm(initialShift)
      setMessage('Shift created successfully.')
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to create shift'))
    }
  }

  const assignShift = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      const payload = { ...assignmentForm }
      if (!payload.end_date) payload.end_date = null
      await api.post('/shift-assignments/', payload)
      setAssignmentForm(initialAssignment)
      setMessage('Shift assigned successfully.')
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to assign shift'))
    }
  }

  const updateShift = (key, value) => {
    setShiftForm(prev => ({ ...prev, [key]: value }))
  }

  const updateAssignment = (key, value) => {
    setAssignmentForm(prev => ({ ...prev, [key]: value }))
  }

  return (
    <section>
      <PageHeader title="Shift Management" subtitle="Create working shifts, weekly offs, grace periods, half-day rules, and overtime rules." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <form className="inlineForm wideForm" onSubmit={createShift}>
        <input placeholder="Shift name" value={shiftForm.name} onChange={e => updateShift('name', e.target.value)} required />
        <input type="time" value={shiftForm.start_time} onChange={e => updateShift('start_time', e.target.value)} required />
        <input type="time" value={shiftForm.end_time} onChange={e => updateShift('end_time', e.target.value)} required />
        <input type="number" placeholder="Break minutes" value={shiftForm.break_minutes} onChange={e => updateShift('break_minutes', Number(e.target.value))} />
        <input type="number" placeholder="Grace minutes" value={shiftForm.grace_minutes} onChange={e => updateShift('grace_minutes', Number(e.target.value))} />
        <input type="number" step="0.5" placeholder="Half day hours" value={shiftForm.half_day_hours} onChange={e => updateShift('half_day_hours', e.target.value)} />
        <input type="number" step="0.5" placeholder="Full day hours" value={shiftForm.full_day_hours} onChange={e => updateShift('full_day_hours', e.target.value)} />
        <input type="number" placeholder="OT grace minutes" value={shiftForm.overtime_after_minutes} onChange={e => updateShift('overtime_after_minutes', Number(e.target.value))} />
        <input placeholder="Weekly off days, e.g. SUN or SAT,SUN" value={shiftForm.weekly_off_days} onChange={e => updateShift('weekly_off_days', e.target.value.toUpperCase())} />
        <label className="checkLabel"><input type="checkbox" checked={shiftForm.is_default} onChange={e => updateShift('is_default', e.target.checked)} /> Default</label>
        <label className="checkLabel"><input type="checkbox" checked={shiftForm.is_active} onChange={e => updateShift('is_active', e.target.checked)} /> Active</label>
        <button>Create Shift</button>
      </form>

      <DataTable columns={[
        { key: 'name', label: 'Shift' },
        { key: 'start_time', label: 'Start' },
        { key: 'end_time', label: 'End' },
        { key: 'break_minutes', label: 'Break' },
        { key: 'grace_minutes', label: 'Grace' },
        { key: 'weekly_off_days', label: 'Weekly Off' },
        { key: 'is_default', label: 'Default', render: row => row.is_default ? 'Yes' : 'No' },
        { key: 'is_active', label: 'Active', render: row => row.is_active ? 'Yes' : 'No' }
      ]} rows={shifts} />

      <PageHeader title="Assign Shift" subtitle="Assign a shift to an employee for a date range." />
      <form className="inlineForm wideForm" onSubmit={assignShift}>
        <select value={assignmentForm.employee} onChange={e => updateAssignment('employee', e.target.value)} required>
          <option value="">Employee</option>
          {employees.map(emp => <option key={emp.id} value={emp.id}>{emp.full_name}</option>)}
        </select>
        <select value={assignmentForm.shift} onChange={e => updateAssignment('shift', e.target.value)} required>
          <option value="">Shift</option>
          {shifts.map(shift => <option key={shift.id} value={shift.id}>{shift.name}</option>)}
        </select>
        <input type="date" value={assignmentForm.start_date} onChange={e => updateAssignment('start_date', e.target.value)} required />
        <input type="date" value={assignmentForm.end_date} onChange={e => updateAssignment('end_date', e.target.value)} />
        <label className="checkLabel"><input type="checkbox" checked={assignmentForm.is_active} onChange={e => updateAssignment('is_active', e.target.checked)} /> Active</label>
        <button>Assign</button>
      </form>

      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'shift_name', label: 'Shift' },
        { key: 'start_date', label: 'Start Date' },
        { key: 'end_date', label: 'End Date' },
        { key: 'is_active', label: 'Active', render: row => row.is_active ? 'Yes' : 'No' }
      ]} rows={assignments} />
    </section>
  )
}
