import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'

const days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
const initialSettings = {
  app_name: 'EmployeeHub',
  country: 'India',
  timezone: 'Asia/Kolkata',
  date_format: 'DD-MM-YYYY',
  currency: 'INR',
  fiscal_year_start_month: 4,
  leave_year_start_month: 1,
  standard_working_hours_per_day: 8,
  attendance_grace_minutes: 10,
  half_day_threshold_hours: 4,
  overtime_rate_per_hour: 0,
  weekly_off_days: ['SATURDAY', 'SUNDAY'],
  default_notice_period_days: 30,
  default_probation_days: 90,
  payroll_lock_day: 7,
  document_max_upload_mb: 10,
  data_retention_days: 2555,
  support_email: '',
  allow_employee_profile_edit: true,
  allow_employee_self_attendance: true,
  allow_employee_expense_submission: true,
  allow_employee_self_enrollment: true,
  enable_ip_restriction: false,
  allowed_ip_ranges: [],
  metadata: {}
}

function showError(err) {
  return JSON.stringify(err.response?.data || err.message || 'Action failed')
}

function StatCard({ label, value }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

export default function Settings() {
  const { user } = useAuth()
  const [settings, setSettings] = useState(initialSettings)
  const [overview, setOverview] = useState(null)
  const [health, setHealth] = useState(null)
  const [backups, setBackups] = useState([])
  const [backupType, setBackupType] = useState('FULL_DB')
  const [backupCommand, setBackupCommand] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const load = async () => {
    setError('')
    try {
      const [settingsRes, overviewRes, healthRes, backupsRes, commandRes] = await Promise.all([
        api.get('/system/settings/'),
        api.get('/system/overview/'),
        api.get('/system/health/'),
        api.get('/backup-logs/'),
        api.get('/backup-logs/backup-command/')
      ])
      setSettings({ ...initialSettings, ...settingsRes.data })
      setOverview(overviewRes.data)
      setHealth(healthRes.data)
      setBackups(backupsRes.data.results || backupsRes.data)
      setBackupCommand(commandRes.data)
    } catch (err) {
      setError(showError(err))
    }
  }

  useEffect(() => { load() }, [])

  const updateSetting = (field, value) => {
    setSettings(prev => ({ ...prev, [field]: value }))
  }

  const toggleWeeklyOff = (day) => {
    setSettings(prev => {
      const selected = prev.weekly_off_days || []
      const next = selected.includes(day) ? selected.filter(item => item !== day) : [...selected, day]
      return { ...prev, weekly_off_days: next }
    })
  }

  const saveSettings = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      const payload = {
        ...settings,
        fiscal_year_start_month: Number(settings.fiscal_year_start_month),
        leave_year_start_month: Number(settings.leave_year_start_month),
        standard_working_hours_per_day: Number(settings.standard_working_hours_per_day),
        attendance_grace_minutes: Number(settings.attendance_grace_minutes),
        half_day_threshold_hours: Number(settings.half_day_threshold_hours),
        overtime_rate_per_hour: Number(settings.overtime_rate_per_hour),
        default_notice_period_days: Number(settings.default_notice_period_days),
        default_probation_days: Number(settings.default_probation_days),
        payroll_lock_day: Number(settings.payroll_lock_day),
        document_max_upload_mb: Number(settings.document_max_upload_mb),
        data_retention_days: Number(settings.data_retention_days)
      }
      const res = await api.patch('/system/settings/', payload)
      setSettings({ ...initialSettings, ...res.data })
      setMessage('System settings saved successfully.')
      await load()
    } catch (err) {
      setError(showError(err))
    }
  }

  const createBackupLog = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.post('/backup-logs/', { backup_type: backupType })
      setMessage('Backup request recorded. Run the generated pg_dump command on the server.')
      await load()
    } catch (err) {
      setError(showError(err))
    }
  }

  const markBackup = async (row, action) => {
    try {
      await api.post(`/backup-logs/${row.id}/${action}/`, {})
      await load()
    } catch (err) {
      setError(showError(err))
    }
  }

  const counts = overview?.counts || {}
  const countCards = useMemo(() => [
    ['Employees', counts.employees || 0],
    ['Attendance', counts.attendance_records || 0],
    ['Leave Requests', counts.leave_requests || 0],
    ['Payroll Runs', counts.payroll_runs || 0],
    ['Assets', counts.assets || 0],
    ['Tickets', counts.support_tickets || 0],
    ['Projects', counts.work_projects || 0],
    ['Audit Logs', counts.audit_logs || 0]
  ], [counts])

  const auditRows = overview?.latest_audits || []

  return (
    <section>
      <PageHeader title="System Settings" subtitle="Organization rules, system health, audit overview, and PostgreSQL backup readiness" />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="statsGrid dashboardStats">
        <StatCard label="Organization" value={user?.organization?.name || '-'} />
        <StatCard label="Role" value={user?.role || '-'} />
        <StatCard label="Database" value={health?.database || '-'} />
        <StatCard label="Debug Mode" value={health?.debug_mode ? 'ON' : 'OFF'} />
      </div>

      <form className="inlineForm settingsForm" onSubmit={saveSettings}>
        <h3>Organization Configuration</h3>
        <input value={settings.app_name || ''} onChange={e => updateSetting('app_name', e.target.value)} placeholder="App name" />
        <input value={settings.country || ''} onChange={e => updateSetting('country', e.target.value)} placeholder="Country" />
        <input value={settings.timezone || ''} onChange={e => updateSetting('timezone', e.target.value)} placeholder="Timezone" />
        <select value={settings.date_format || 'DD-MM-YYYY'} onChange={e => updateSetting('date_format', e.target.value)}>
          <option value="DD-MM-YYYY">DD-MM-YYYY</option>
          <option value="MM-DD-YYYY">MM-DD-YYYY</option>
          <option value="YYYY-MM-DD">YYYY-MM-DD</option>
        </select>
        <input value={settings.currency || ''} onChange={e => updateSetting('currency', e.target.value)} placeholder="Currency" />
        <input type="number" value={settings.fiscal_year_start_month || 4} onChange={e => updateSetting('fiscal_year_start_month', e.target.value)} placeholder="Fiscal start month" />
        <input type="number" value={settings.leave_year_start_month || 1} onChange={e => updateSetting('leave_year_start_month', e.target.value)} placeholder="Leave year start month" />
        <input value={settings.support_email || ''} onChange={e => updateSetting('support_email', e.target.value)} placeholder="Support email" />

        <h3>HR, Attendance and Payroll Rules</h3>
        <input type="number" step="0.25" value={settings.standard_working_hours_per_day || 8} onChange={e => updateSetting('standard_working_hours_per_day', e.target.value)} placeholder="Working hours/day" />
        <input type="number" value={settings.attendance_grace_minutes || 0} onChange={e => updateSetting('attendance_grace_minutes', e.target.value)} placeholder="Grace minutes" />
        <input type="number" step="0.25" value={settings.half_day_threshold_hours || 4} onChange={e => updateSetting('half_day_threshold_hours', e.target.value)} placeholder="Half-day threshold" />
        <input type="number" step="0.01" value={settings.overtime_rate_per_hour || 0} onChange={e => updateSetting('overtime_rate_per_hour', e.target.value)} placeholder="Overtime rate/hour" />
        <input type="number" value={settings.default_notice_period_days || 30} onChange={e => updateSetting('default_notice_period_days', e.target.value)} placeholder="Notice period days" />
        <input type="number" value={settings.default_probation_days || 90} onChange={e => updateSetting('default_probation_days', e.target.value)} placeholder="Probation days" />
        <input type="number" value={settings.payroll_lock_day || 7} onChange={e => updateSetting('payroll_lock_day', e.target.value)} placeholder="Payroll lock day" />
        <input type="number" value={settings.document_max_upload_mb || 10} onChange={e => updateSetting('document_max_upload_mb', e.target.value)} placeholder="Max upload MB" />
        <input type="number" value={settings.data_retention_days || 2555} onChange={e => updateSetting('data_retention_days', e.target.value)} placeholder="Data retention days" />

        <div className="rolePicker">
          <small>Weekly off days</small>
          <div>
            {days.map(day => (
              <label className="checkLabel" key={day}>
                <input type="checkbox" checked={(settings.weekly_off_days || []).includes(day)} onChange={() => toggleWeeklyOff(day)} />
                {day}
              </label>
            ))}
          </div>
        </div>

        <div className="rolePicker">
          <small>Employee self-service permissions</small>
          <div>
            <label className="checkLabel"><input type="checkbox" checked={settings.allow_employee_profile_edit} onChange={e => updateSetting('allow_employee_profile_edit', e.target.checked)} /> Profile edit</label>
            <label className="checkLabel"><input type="checkbox" checked={settings.allow_employee_self_attendance} onChange={e => updateSetting('allow_employee_self_attendance', e.target.checked)} /> Self attendance</label>
            <label className="checkLabel"><input type="checkbox" checked={settings.allow_employee_expense_submission} onChange={e => updateSetting('allow_employee_expense_submission', e.target.checked)} /> Expense submission</label>
            <label className="checkLabel"><input type="checkbox" checked={settings.allow_employee_self_enrollment} onChange={e => updateSetting('allow_employee_self_enrollment', e.target.checked)} /> LMS self-enrollment</label>
            <label className="checkLabel"><input type="checkbox" checked={settings.enable_ip_restriction} onChange={e => updateSetting('enable_ip_restriction', e.target.checked)} /> IP restriction</label>
          </div>
        </div>
        <button type="submit">Save Settings</button>
      </form>

      <div className="statsGrid dashboardStats">
        {countCards.map(([label, value]) => <StatCard key={label} label={label} value={value} />)}
      </div>

      <div className="settingsCard">
        <h3>PostgreSQL Backup Readiness</h3>
        <p className="mutedText">The application records backup requests. Run the command on the production server where Docker Compose is running.</p>
        <form className="inlineForm" onSubmit={createBackupLog}>
          <select value={backupType} onChange={e => setBackupType(e.target.value)}>
            <option value="FULL_DB">Full Database</option>
            <option value="SCHEMA_ONLY">Schema Only</option>
            <option value="DATA_ONLY">Data Only</option>
            <option value="MANUAL_EXPORT">Manual Export</option>
          </select>
          <button type="submit">Record Backup Request</button>
        </form>
        {backupCommand && (
          <div className="infoCard">
            <strong>Backup command</strong>
            <code>{backupCommand.command}</code>
            <strong>Restore command</strong>
            <code>{backupCommand.restore_command}</code>
          </div>
        )}
        <DataTable
          columns={[
            { key: 'created_at', label: 'Requested', render: row => new Date(row.created_at).toLocaleString() },
            { key: 'backup_type', label: 'Type' },
            { key: 'status', label: 'Status' },
            { key: 'file_name', label: 'File' },
            { key: 'requested_by_email', label: 'Requested By' },
            { key: 'actions', label: 'Actions', render: row => (
              <div className="actions">
                <button type="button" onClick={() => markBackup(row, 'mark-running')}>Running</button>
                <button type="button" onClick={() => markBackup(row, 'mark-completed')}>Completed</button>
                <button type="button" className="dangerBtn" onClick={() => markBackup(row, 'mark-failed')}>Failed</button>
              </div>
            )}
          ]}
          rows={backups}
        />
      </div>

      <div className="settingsCard">
        <h3>Latest Audit Events</h3>
        <DataTable
          columns={[
            { key: 'created_at', label: 'Time', render: row => new Date(row.created_at).toLocaleString() },
            { key: 'actor', label: 'Actor' },
            { key: 'action', label: 'Action' },
            { key: 'entity', label: 'Entity' },
            { key: 'entity_id', label: 'Entity ID' }
          ]}
          rows={auditRows}
        />
      </div>
    </section>
  )
}
