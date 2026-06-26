import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { MANAGER_ROLES, hasRole } from '../utils/roles.js'

const initialProject = {
  project_code: '', name: '', client_name: '', description: '', project_manager: '', start_date: '', end_date: '', status: 'ACTIVE', is_billable: true, budget_hours: '0'
}
const initialMember = { project: '', employee: '', project_role: 'MEMBER', hourly_rate: '0', is_active: true, assigned_at: '', released_at: '' }
const initialTask = { project: '', title: '', description: '', assigned_to: '', status: 'TODO', priority: 'MEDIUM', estimated_hours: '0', due_date: '' }
const initialEntry = { employee: '', project: '', task: '', work_date: '', start_time: '', end_time: '', hours: '', is_billable: true, description: '' }

export default function Timesheets() {
  const { user } = useAuth()
  const canManage = hasRole(user, MANAGER_ROLES)
  const [projects, setProjects] = useState([])
  const [memberships, setMemberships] = useState([])
  const [tasks, setTasks] = useState([])
  const [entries, setEntries] = useState([])
  const [employees, setEmployees] = useState([])
  const [summary, setSummary] = useState([])
  const [summaryTotals, setSummaryTotals] = useState({})
  const [projectForm, setProjectForm] = useState(initialProject)
  const [memberForm, setMemberForm] = useState(initialMember)
  const [taskForm, setTaskForm] = useState(initialTask)
  const [entryForm, setEntryForm] = useState(initialEntry)
  const now = new Date()
  const [filter, setFilter] = useState({ month: String(now.getMonth() + 1), year: String(now.getFullYear()) })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const normalize = data => data.results || data

  const showError = (err) => {
    setMessage('')
    setError(err?.response?.data?.detail || JSON.stringify(err?.response?.data || {}) || 'Something went wrong')
  }

  const showMessage = (text) => {
    setError('')
    setMessage(text)
  }

  const cleanPayload = (payload) => {
    const output = { ...payload }
    Object.keys(output).forEach(key => {
      if (output[key] === '') output[key] = null
    })
    return output
  }

  const load = async () => {
    const responses = await Promise.all([
      api.get('/work-projects/'),
      api.get('/project-memberships/'),
      api.get('/project-tasks/'),
      api.get('/timesheet-entries/'),
      api.get('/employees/'),
      api.get(`/timesheets/monthly-summary/?month=${filter.month}&year=${filter.year}`)
    ])
    setProjects(normalize(responses[0].data))
    setMemberships(normalize(responses[1].data))
    setTasks(normalize(responses[2].data))
    setEntries(normalize(responses[3].data))
    setEmployees(normalize(responses[4].data))
    setSummary((responses[5].data.results || []).map((item, index) => ({ ...item, id: item.employee_id || index })))
    setSummaryTotals(responses[5].data.totals || {})
  }

  useEffect(() => { load().catch(showError) }, [filter.month, filter.year])

  const createProject = async (e) => {
    e.preventDefault()
    try {
      await api.post('/work-projects/', cleanPayload(projectForm))
      setProjectForm(initialProject)
      await load()
      showMessage('Project created.')
    } catch (err) {
      showError(err)
    }
  }

  const createMembership = async (e) => {
    e.preventDefault()
    try {
      await api.post('/project-memberships/', cleanPayload(memberForm))
      setMemberForm(initialMember)
      await load()
      showMessage('Project member added.')
    } catch (err) {
      showError(err)
    }
  }

  const createTask = async (e) => {
    e.preventDefault()
    try {
      await api.post('/project-tasks/', cleanPayload(taskForm))
      setTaskForm(initialTask)
      await load()
      showMessage('Project task created.')
    } catch (err) {
      showError(err)
    }
  }

  const createEntry = async (e) => {
    e.preventDefault()
    try {
      const payload = cleanPayload(entryForm)
      if (!canManage) delete payload.employee
      await api.post('/timesheet-entries/', payload)
      setEntryForm(initialEntry)
      await load()
      showMessage('Timesheet entry saved as draft.')
    } catch (err) {
      showError(err)
    }
  }

  const projectAction = async (row, action, success = 'Project updated.') => {
    try {
      await api.post(`/work-projects/${row.id}/${action}/`)
      await load()
      showMessage(success)
    } catch (err) {
      showError(err)
    }
  }

  const memberAction = async (row, action, success = 'Membership updated.') => {
    try {
      await api.post(`/project-memberships/${row.id}/${action}/`)
      await load()
      showMessage(success)
    } catch (err) {
      showError(err)
    }
  }

  const taskAction = async (row, action, success = 'Task updated.') => {
    try {
      await api.post(`/project-tasks/${row.id}/${action}/`)
      await load()
      showMessage(success)
    } catch (err) {
      showError(err)
    }
  }

  const entryAction = async (row, action, payload = {}, success = 'Timesheet updated.') => {
    try {
      await api.post(`/timesheet-entries/${row.id}/${action}/`, payload)
      await load()
      showMessage(success)
    } catch (err) {
      showError(err)
    }
  }

  const approveEntry = async (row) => {
    const approvedHours = window.prompt('Approved hours', row.hours)
    if (approvedHours === null) return
    await entryAction(row, 'approve', { approved_hours: approvedHours }, 'Timesheet approved.')
  }

  const rejectEntry = async (row) => {
    const reason = window.prompt('Rejection reason', row.rejection_reason || '')
    if (reason === null) return
    await entryAction(row, 'reject', { rejection_reason: reason }, 'Timesheet rejected.')
  }

  const projectTaskOptions = tasks.filter(item => !entryForm.project || String(item.project) === String(entryForm.project))
  const memberEmployees = employees.filter(item => item.status !== 'EXITED')

  return (
    <div>
      <PageHeader title="Timesheets" subtitle="Manage projects, tasks, daily worklogs, approvals, billable hours, and monthly timesheet reports." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="statsGrid smallStats">
        <div className="stat"><span>Projects</span><strong>{projects.length}</strong></div>
        <div className="stat"><span>Draft Entries</span><strong>{entries.filter(item => item.status === 'DRAFT').length}</strong></div>
        <div className="stat"><span>Pending Approval</span><strong>{entries.filter(item => item.status === 'SUBMITTED').length}</strong></div>
        <div className="stat"><span>Approved Hours</span><strong>{summaryTotals.approved_hours || 0}</strong></div>
      </div>

      {canManage && (
        <form className="inlineForm wideForm" onSubmit={createProject}>
          <input placeholder="Project code" value={projectForm.project_code} onChange={e => setProjectForm({ ...projectForm, project_code: e.target.value })} required />
          <input placeholder="Project name" value={projectForm.name} onChange={e => setProjectForm({ ...projectForm, name: e.target.value })} required />
          <input placeholder="Client name" value={projectForm.client_name} onChange={e => setProjectForm({ ...projectForm, client_name: e.target.value })} />
          <select value={projectForm.project_manager || ''} onChange={e => setProjectForm({ ...projectForm, project_manager: e.target.value })}>
            <option value="">Project manager</option>
            {memberEmployees.map(item => <option key={item.id} value={item.id}>{item.employee_code} - {item.user_email}</option>)}
          </select>
          <input type="date" value={projectForm.start_date || ''} onChange={e => setProjectForm({ ...projectForm, start_date: e.target.value })} />
          <input type="date" value={projectForm.end_date || ''} onChange={e => setProjectForm({ ...projectForm, end_date: e.target.value })} />
          <select value={projectForm.status} onChange={e => setProjectForm({ ...projectForm, status: e.target.value })}>
            <option value="PLANNED">Planned</option>
            <option value="ACTIVE">Active</option>
            <option value="ON_HOLD">On Hold</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
          <input type="number" step="0.25" placeholder="Budget hours" value={projectForm.budget_hours} onChange={e => setProjectForm({ ...projectForm, budget_hours: e.target.value })} />
          <label className="checkLabel"><input type="checkbox" checked={projectForm.is_billable} onChange={e => setProjectForm({ ...projectForm, is_billable: e.target.checked })} /> Billable</label>
          <textarea placeholder="Description" value={projectForm.description} onChange={e => setProjectForm({ ...projectForm, description: e.target.value })} />
          <button>Create Project</button>
        </form>
      )}

      <DataTable
        columns={[
          { key: 'project_code', label: 'Code' },
          { key: 'name', label: 'Project' },
          { key: 'client_name', label: 'Client' },
          { key: 'project_manager_email', label: 'Manager' },
          { key: 'status', label: 'Status' },
          { key: 'is_billable', label: 'Billable', render: row => row.is_billable ? 'Yes' : 'No' },
          { key: 'member_count', label: 'Members' },
          { key: 'task_count', label: 'Tasks' },
          { key: 'approved_hours_total', label: 'Approved Hours' },
          { key: 'actions', label: 'Actions', render: row => canManage ? <div className="actions"><button onClick={() => projectAction(row, 'activate')}>Activate</button><button onClick={() => projectAction(row, 'hold')}>Hold</button><button onClick={() => projectAction(row, 'complete')}>Complete</button></div> : '-' }
        ]}
        rows={projects}
      />

      {canManage && (
        <form className="inlineForm wideForm" onSubmit={createMembership}>
          <select value={memberForm.project || ''} onChange={e => setMemberForm({ ...memberForm, project: e.target.value })} required>
            <option value="">Project</option>
            {projects.map(item => <option key={item.id} value={item.id}>{item.project_code} - {item.name}</option>)}
          </select>
          <select value={memberForm.employee || ''} onChange={e => setMemberForm({ ...memberForm, employee: e.target.value })} required>
            <option value="">Employee</option>
            {memberEmployees.map(item => <option key={item.id} value={item.id}>{item.employee_code} - {item.user_email}</option>)}
          </select>
          <select value={memberForm.project_role} onChange={e => setMemberForm({ ...memberForm, project_role: e.target.value })}>
            <option value="MEMBER">Member</option>
            <option value="LEAD">Lead</option>
            <option value="MANAGER">Manager</option>
            <option value="QA">QA</option>
          </select>
          <input type="number" step="0.01" placeholder="Hourly rate" value={memberForm.hourly_rate} onChange={e => setMemberForm({ ...memberForm, hourly_rate: e.target.value })} />
          <input type="date" value={memberForm.assigned_at || ''} onChange={e => setMemberForm({ ...memberForm, assigned_at: e.target.value })} />
          <button>Add Member</button>
        </form>
      )}

      <DataTable
        columns={[
          { key: 'project_code', label: 'Project' },
          { key: 'employee_code', label: 'Employee Code' },
          { key: 'employee_email', label: 'Employee' },
          { key: 'project_role', label: 'Role' },
          { key: 'hourly_rate', label: 'Rate' },
          { key: 'is_active', label: 'Active', render: row => row.is_active ? 'Yes' : 'No' },
          { key: 'actions', label: 'Actions', render: row => canManage ? <div className="actions"><button onClick={() => memberAction(row, 'release', 'Member released.')}>Release</button><button onClick={() => memberAction(row, 'reactivate', 'Member reactivated.')}>Reactivate</button></div> : '-' }
        ]}
        rows={memberships}
      />

      {canManage && (
        <form className="inlineForm wideForm" onSubmit={createTask}>
          <select value={taskForm.project || ''} onChange={e => setTaskForm({ ...taskForm, project: e.target.value })} required>
            <option value="">Project</option>
            {projects.map(item => <option key={item.id} value={item.id}>{item.project_code} - {item.name}</option>)}
          </select>
          <input placeholder="Task title" value={taskForm.title} onChange={e => setTaskForm({ ...taskForm, title: e.target.value })} required />
          <select value={taskForm.assigned_to || ''} onChange={e => setTaskForm({ ...taskForm, assigned_to: e.target.value })}>
            <option value="">Assign to</option>
            {memberEmployees.map(item => <option key={item.id} value={item.id}>{item.employee_code} - {item.user_email}</option>)}
          </select>
          <select value={taskForm.priority} onChange={e => setTaskForm({ ...taskForm, priority: e.target.value })}>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>
          <input type="number" step="0.25" placeholder="Estimated hours" value={taskForm.estimated_hours} onChange={e => setTaskForm({ ...taskForm, estimated_hours: e.target.value })} />
          <input type="date" value={taskForm.due_date || ''} onChange={e => setTaskForm({ ...taskForm, due_date: e.target.value })} />
          <textarea placeholder="Task description" value={taskForm.description} onChange={e => setTaskForm({ ...taskForm, description: e.target.value })} />
          <button>Create Task</button>
        </form>
      )}

      <DataTable
        columns={[
          { key: 'project_code', label: 'Project' },
          { key: 'title', label: 'Task' },
          { key: 'assigned_to_email', label: 'Assigned To' },
          { key: 'status', label: 'Status' },
          { key: 'priority', label: 'Priority' },
          { key: 'estimated_hours', label: 'Est. Hours' },
          { key: 'due_date', label: 'Due' },
          { key: 'actions', label: 'Actions', render: row => <div className="actions"><button onClick={() => taskAction(row, 'start')}>Start</button><button onClick={() => taskAction(row, 'review')}>Review</button><button onClick={() => taskAction(row, 'done')}>Done</button><button onClick={() => taskAction(row, 'blocked')}>Blocked</button></div> }
        ]}
        rows={tasks}
      />

      <form className="inlineForm wideForm" onSubmit={createEntry}>
        {canManage && (
          <select value={entryForm.employee || ''} onChange={e => setEntryForm({ ...entryForm, employee: e.target.value })}>
            <option value="">Employee</option>
            {memberEmployees.map(item => <option key={item.id} value={item.id}>{item.employee_code} - {item.user_email}</option>)}
          </select>
        )}
        <select value={entryForm.project || ''} onChange={e => setEntryForm({ ...entryForm, project: e.target.value, task: '' })} required>
          <option value="">Project</option>
          {projects.filter(item => item.status === 'ACTIVE' || item.status === 'PLANNED').map(item => <option key={item.id} value={item.id}>{item.project_code} - {item.name}</option>)}
        </select>
        <select value={entryForm.task || ''} onChange={e => setEntryForm({ ...entryForm, task: e.target.value })}>
          <option value="">Task</option>
          {projectTaskOptions.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select>
        <input type="date" value={entryForm.work_date || ''} onChange={e => setEntryForm({ ...entryForm, work_date: e.target.value })} required />
        <input type="time" value={entryForm.start_time || ''} onChange={e => setEntryForm({ ...entryForm, start_time: e.target.value })} />
        <input type="time" value={entryForm.end_time || ''} onChange={e => setEntryForm({ ...entryForm, end_time: e.target.value })} />
        <input type="number" step="0.25" min="0.25" max="24" placeholder="Hours" value={entryForm.hours} onChange={e => setEntryForm({ ...entryForm, hours: e.target.value })} required />
        <label className="checkLabel"><input type="checkbox" checked={entryForm.is_billable} onChange={e => setEntryForm({ ...entryForm, is_billable: e.target.checked })} /> Billable</label>
        <textarea placeholder="Work description" value={entryForm.description} onChange={e => setEntryForm({ ...entryForm, description: e.target.value })} required />
        <button>Save Timesheet</button>
      </form>

      <DataTable
        columns={[
          { key: 'work_date', label: 'Date' },
          { key: 'employee_email', label: 'Employee' },
          { key: 'project_code', label: 'Project' },
          { key: 'task_title', label: 'Task' },
          { key: 'hours', label: 'Hours' },
          { key: 'approved_hours', label: 'Approved' },
          { key: 'is_billable', label: 'Billable', render: row => row.is_billable ? 'Yes' : 'No' },
          { key: 'status', label: 'Status' },
          { key: 'reviewed_by_email', label: 'Reviewed By' },
          { key: 'actions', label: 'Actions', render: row => <div className="actions"><button onClick={() => entryAction(row, 'submit', {}, 'Timesheet submitted.')}>Submit</button>{canManage && <button onClick={() => approveEntry(row)}>Approve</button>}{canManage && <button onClick={() => rejectEntry(row)}>Reject</button>}{canManage && <button onClick={() => entryAction(row, 'reopen', {}, 'Timesheet reopened.')}>Reopen</button>}</div> }
        ]}
        rows={entries}
      />

      <div className="sectionHeader">
        <h3>Monthly Timesheet Summary</h3>
        <div className="actions">
          <input type="number" min="1" max="12" value={filter.month} onChange={e => setFilter({ ...filter, month: e.target.value })} />
          <input type="number" value={filter.year} onChange={e => setFilter({ ...filter, year: e.target.value })} />
        </div>
      </div>

      <DataTable
        columns={[
          { key: 'employee_code', label: 'Code' },
          { key: 'employee_email', label: 'Employee' },
          { key: 'submitted_hours', label: 'Submitted Hours' },
          { key: 'approved_hours', label: 'Approved Hours' },
          { key: 'billable_hours', label: 'Billable Hours' },
          { key: 'non_billable_hours', label: 'Non-Billable Hours' },
          { key: 'draft_count', label: 'Draft' },
          { key: 'submitted_count', label: 'Pending' },
          { key: 'approved_count', label: 'Approved' },
          { key: 'rejected_count', label: 'Rejected' }
        ]}
        rows={summary}
      />
    </div>
  )
}
