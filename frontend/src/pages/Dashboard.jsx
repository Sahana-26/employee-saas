import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client.js'
import PageHeader from '../components/PageHeader.jsx'

const currentDate = new Date()

function minutesToHours(minutes) {
  if (!minutes) return '0h'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${h}h ${m}m`
}

function currency(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(Number(value || 0))
}

function numberValue(value) {
  if (value === undefined || value === null) return 0
  return Number(value)
}

function StatCard({ label, value, helper }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {helper && <small>{helper}</small>}
    </div>
  )
}

function MiniBar({ label, value, max }) {
  const width = max ? Math.min((Number(value || 0) / max) * 100, 100) : 0
  return (
    <div className="miniBarRow">
      <div className="miniBarLabel">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="miniBarTrack">
        <div className="miniBarFill" style={{ width: `${width}%` }} />
      </div>
    </div>
  )
}

function SimpleBarChart({ title, rows, labelKey = 'label', valueKey = 'value', formatter = value => value }) {
  const max = useMemo(() => Math.max(...rows.map(row => Number(row[valueKey] || 0)), 0), [rows, valueKey])
  return (
    <div className="chartCard">
      <h3>{title}</h3>
      {rows.length === 0 && <p className="mutedText">No data available.</p>}
      {rows.map((row, index) => (
        <MiniBar
          key={`${row[labelKey]}-${index}`}
          label={row[labelKey] || 'Unknown'}
          value={formatter(row[valueKey])}
          max={max}
        />
      ))}
    </div>
  )
}

function DailyTrend({ rows }) {
  const visibleRows = rows.slice(-14)
  const max = Math.max(...visibleRows.map(row => Number(row.present || 0) + Number(row.leave || 0) + Number(row.absent || 0)), 1)

  return (
    <div className="chartCard wideChart">
      <h3>Last 14 Days Attendance Trend</h3>
      <div className="trendChart">
        {visibleRows.map(row => {
          const total = Number(row.present || 0) + Number(row.leave || 0) + Number(row.absent || 0)
          const height = Math.max((total / max) * 140, total ? 12 : 4)
          const dateText = new Date(row.date).getDate()
          return (
            <div className="trendItem" key={row.date}>
              <div className="trendStack" style={{ height: `${height}px` }}>
                <div style={{ height: `${total ? (Number(row.present || 0) / total) * 100 : 0}%` }} title={`Present: ${row.present}`} />
                <div style={{ height: `${total ? (Number(row.leave || 0) / total) * 100 : 0}%` }} title={`Leave: ${row.leave}`} />
                <div style={{ height: `${total ? (Number(row.absent || 0) / total) * 100 : 0}%` }} title={`Absent: ${row.absent}`} />
              </div>
              <span>{dateText}</span>
            </div>
          )
        })}
      </div>
      <div className="legendRow">
        <span>Present</span>
        <span>Leave</span>
        <span>Absent</span>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [month, setMonth] = useState(String(currentDate.getMonth() + 1))
  const [year, setYear] = useState(String(currentDate.getFullYear()))
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get(`/reports/dashboard-summary/?month=${month}&year=${year}`)
      setSummary(res.data)
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to load dashboard summary'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const applyFilter = (e) => {
    e.preventDefault()
    load()
  }

  const cards = summary?.cards || {}
  const departmentRows = summary?.department_summary || []
  const departmentChartRows = departmentRows.map(row => ({
    label: row.department,
    value: row.employees,
    late_count: row.late_count,
    overtime_minutes: row.overtime_minutes
  }))
  const leaveStatusRows = Object.entries(summary?.leave_status_summary || {}).map(([label, value]) => ({ label, value }))
  const payrollRows = summary?.payroll_status_summary?.map(row => ({ label: row.status, value: row.net })) || []

  return (
    <section>
      <PageHeader title="Dashboard" subtitle="HR, attendance, leave, and payroll analytics overview." />
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
        <button>Refresh Dashboard</button>
      </form>

      {loading && <div className="infoCard">Loading dashboard analytics...</div>}

      {summary && (
        <>
          <div className="statsGrid dashboardStats">
            <StatCard label="Total Employees" value={cards.total_employees} helper={`${cards.active_employees || 0} active`} />
            <StatCard label="Departments" value={cards.departments} />
            <StatCard label="Today Present" value={cards.today_present} helper={`${cards.today_late || 0} late today`} />
            <StatCard label="Today Absent" value={cards.today_absent} />
            <StatCard label="Pending Leaves" value={cards.pending_leaves} />
            <StatCard label="Month Leave Days" value={cards.month_leave_days} />
            <StatCard label="Worked Hours" value={minutesToHours(cards.worked_minutes)} />
            <StatCard label="Overtime" value={minutesToHours(cards.overtime_minutes)} />
            <StatCard label="Payslips" value={cards.payslip_count} helper={cards.payroll_status} />
            <StatCard label="Payroll Net" value={currency(cards.payroll_net)} />
            <StatCard label="Payroll Gross" value={currency(cards.payroll_gross)} />
            <StatCard label="Deductions" value={currency(cards.payroll_deductions)} />
          </div>

          <div className="analyticsGrid">
            <SimpleBarChart
              title="Monthly Attendance Mix"
              rows={summary.attendance_mix || []}
              formatter={value => numberValue(value)}
            />
            <SimpleBarChart
              title="Department Headcount"
              rows={departmentChartRows}
              formatter={value => numberValue(value)}
            />
            <SimpleBarChart
              title="Leave Status"
              rows={leaveStatusRows}
              formatter={value => numberValue(value)}
            />
            <SimpleBarChart
              title="Payroll by Status"
              rows={payrollRows}
              formatter={value => currency(value)}
            />
          </div>

          <DailyTrend rows={summary.daily_trend || []} />

          <div className="tableCard dashboardTable">
            <table>
              <thead>
                <tr>
                  <th>Department</th>
                  <th>Employees</th>
                  <th>Active</th>
                  <th>Attendance Records</th>
                  <th>Late Count</th>
                  <th>Worked Hours</th>
                  <th>Overtime</th>
                </tr>
              </thead>
              <tbody>
                {departmentRows.map(row => (
                  <tr key={row.department_id}>
                    <td>{row.department}</td>
                    <td>{row.employees}</td>
                    <td>{row.active_employees}</td>
                    <td>{row.attendance_records}</td>
                    <td>{row.late_count}</td>
                    <td>{minutesToHours(row.worked_minutes)}</td>
                    <td>{minutesToHours(row.overtime_minutes)}</td>
                  </tr>
                ))}
                {departmentRows.length === 0 && (
                  <tr><td colSpan="7">No department analytics available.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
