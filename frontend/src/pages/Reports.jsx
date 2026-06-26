import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'

function minutesToHours(minutes) {
  if (!minutes) return '0h'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${h}h ${m}m`
}

const currentDate = new Date()

export default function Reports() {
  const [month, setMonth] = useState(String(currentDate.getMonth() + 1))
  const [year, setYear] = useState(String(currentDate.getFullYear()))
  const [attendanceRows, setAttendanceRows] = useState([])
  const [leaveBalanceRows, setLeaveBalanceRows] = useState([])
  const [totals, setTotals] = useState(null)
  const [error, setError] = useState('')

  const load = async () => {
    setError('')
    try {
      const [attendanceRes, leaveBalanceRes] = await Promise.all([
        api.get(`/reports/monthly-attendance/?month=${month}&year=${year}`),
        api.get(`/reports/leave-balances/?year=${year}`)
      ])
      setAttendanceRows(attendanceRes.data.results || [])
      setTotals(attendanceRes.data.totals || null)
      setLeaveBalanceRows(leaveBalanceRes.data.results || [])
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to load reports'))
    }
  }

  useEffect(() => { load() }, [])

  const applyFilter = (e) => {
    e.preventDefault()
    load()
  }

  return (
    <section>
      <PageHeader title="Reports" subtitle="Monthly attendance summary and leave balance report." />
      {error && <div className="error">{error}</div>}

      <form className="inlineForm" onSubmit={applyFilter}>
        <select value={month} onChange={e => setMonth(e.target.value)}>
          <option value="1">January</option>
          <option value="2">February</option>
          <option value="3">March</option>
          <option value="4">April</option>
          <option value="5">May</option>
          <option value="6">June</option>
          <option value="7">July</option>
          <option value="8">August</option>
          <option value="9">September</option>
          <option value="10">October</option>
          <option value="11">November</option>
          <option value="12">December</option>
        </select>
        <input type="number" value={year} onChange={e => setYear(e.target.value)} placeholder="Year" />
        <button>Apply</button>
      </form>

      {totals && (
        <div className="statsGrid smallStats">
          <div className="stat"><span>Employees</span><strong>{totals.employees}</strong></div>
          <div className="stat"><span>Expected Work Days</span><strong>{totals.expected_work_days}</strong></div>
          <div className="stat"><span>Present Days</span><strong>{totals.present_days}</strong></div>
          <div className="stat"><span>Absent Days</span><strong>{totals.absent_days}</strong></div>
          <div className="stat"><span>Leave Days</span><strong>{totals.leave_days}</strong></div>
          <div className="stat"><span>Late Count</span><strong>{totals.late_count}</strong></div>
          <div className="stat"><span>Worked Hours</span><strong>{minutesToHours(totals.worked_minutes)}</strong></div>
          <div className="stat"><span>Overtime</span><strong>{minutesToHours(totals.overtime_minutes)}</strong></div>
        </div>
      )}

      <PageHeader title="Monthly Attendance Report" subtitle="Employee-wise monthly attendance status calculated from shifts, holidays, leaves, and attendance records." />
      <DataTable columns={[
        { key: 'employee_code', label: 'Code' },
        { key: 'employee_name', label: 'Employee' },
        { key: 'department', label: 'Department' },
        { key: 'expected_work_days', label: 'Work Days' },
        { key: 'present_days', label: 'Present' },
        { key: 'half_days', label: 'Half Days' },
        { key: 'leave_days', label: 'Leave' },
        { key: 'absent_days', label: 'Absent' },
        { key: 'holiday_days', label: 'Holidays' },
        { key: 'weekly_off_days', label: 'Week Off' },
        { key: 'late_count', label: 'Late Count' },
        { key: 'worked_minutes', label: 'Worked', render: row => minutesToHours(row.worked_minutes) },
        { key: 'late_minutes', label: 'Late Minutes', render: row => `${row.late_minutes || 0} min` },
        { key: 'overtime_minutes', label: 'Overtime', render: row => minutesToHours(row.overtime_minutes) }
      ]} rows={attendanceRows.map(row => ({ ...row, id: row.employee_id }))} />

      <PageHeader title="Leave Balance Report" subtitle="Approved leaves are deducted automatically from the yearly leave balance." />
      <DataTable columns={[
        { key: 'employee_code', label: 'Code' },
        { key: 'employee_name', label: 'Employee' },
        { key: 'department', label: 'Department' },
        { key: 'leave_type', label: 'Leave Type' },
        { key: 'allocated', label: 'Allocated' },
        { key: 'used', label: 'Used' },
        { key: 'remaining', label: 'Remaining' }
      ]} rows={leaveBalanceRows.map((row, index) => ({ ...row, id: `${row.employee_id}-${row.leave_type}-${index}` }))} />
    </section>
  )
}
