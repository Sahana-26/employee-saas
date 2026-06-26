import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { HELPDESK_ROLES, hasRole } from '../utils/roles.js'

const initialCategory = { name: '', description: '', default_assignee: '', is_active: true }
const initialTicket = { requested_by: '', category: '', assigned_to: '', subject: '', description: '', priority: 'MEDIUM', source: 'EMPLOYEE_PORTAL', due_at: '' }
const initialAttachment = { ticket: '', title: '', notes: '' }

export default function Helpdesk() {
  const { user } = useAuth()
  const canManage = hasRole(user, HELPDESK_ROLES)
  const [categories, setCategories] = useState([])
  const [tickets, setTickets] = useState([])
  const [comments, setComments] = useState([])
  const [attachments, setAttachments] = useState([])
  const [employees, setEmployees] = useState([])
  const [categoryForm, setCategoryForm] = useState(initialCategory)
  const [ticketForm, setTicketForm] = useState(initialTicket)
  const [attachmentForm, setAttachmentForm] = useState(initialAttachment)
  const [attachmentFile, setAttachmentFile] = useState(null)
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

  const load = async () => {
    const requests = [
      api.get('/ticket-categories/'),
      api.get('/support-tickets/'),
      api.get('/ticket-comments/'),
      api.get('/ticket-attachments/')
    ]
    if (canManage) {
      requests.push(api.get('/employees/'))
    }
    const responses = await Promise.all(requests)
    setCategories(normalize(responses[0].data))
    setTickets(normalize(responses[1].data))
    setComments(normalize(responses[2].data))
    setAttachments(normalize(responses[3].data))
    if (canManage) {
      setEmployees(normalize(responses[4].data))
    }
  }

  useEffect(() => { load().catch(showError) }, [canManage])

  const cleanPayload = (payload) => {
    const output = { ...payload }
    Object.keys(output).forEach(key => {
      if (output[key] === '') output[key] = null
    })
    return output
  }

  const createCategory = async (e) => {
    e.preventDefault()
    try {
      await api.post('/ticket-categories/', cleanPayload(categoryForm))
      setCategoryForm(initialCategory)
      await load()
      showMessage('Ticket category created.')
    } catch (err) {
      showError(err)
    }
  }

  const createTicket = async (e) => {
    e.preventDefault()
    try {
      const payload = cleanPayload(ticketForm)
      if (!canManage) delete payload.requested_by
      if (!canManage) delete payload.assigned_to
      await api.post('/support-tickets/', payload)
      setTicketForm(initialTicket)
      await load()
      showMessage('Support ticket created.')
    } catch (err) {
      showError(err)
    }
  }

  const ticketAction = async (row, action, payload = {}, success = 'Ticket updated.') => {
    try {
      await api.post(`/support-tickets/${row.id}/${action}/`, payload)
      await load()
      showMessage(success)
    } catch (err) {
      showError(err)
    }
  }

  const assignTicket = async (row) => {
    const assignedTo = window.prompt('Enter user ID to assign', row.assigned_to || '')
    if (assignedTo === null) return
    const dueAt = window.prompt('Due date/time in ISO format, optional', row.due_at || '')
    await ticketAction(row, 'assign', cleanPayload({ assigned_to: assignedTo, due_at: dueAt }), 'Ticket assigned.')
  }

  const pendingUser = async (row) => {
    const text = window.prompt('Message to employee', 'Please share more information.')
    if (text === null) return
    await ticketAction(row, 'pending-user', { message: text }, 'Ticket marked pending user response.')
  }

  const resolveTicket = async (row) => {
    const text = window.prompt('Resolution notes', row.resolution_notes || '')
    if (text === null) return
    await ticketAction(row, 'resolve', { resolution_notes: text }, 'Ticket resolved.')
  }

  const addComment = async (row) => {
    const text = window.prompt('Comment')
    if (!text) return
    const internal = canManage && window.confirm('Make this an internal support note?')
    await ticketAction(row, 'add-comment', { message: text, is_internal: internal }, 'Comment added.')
  }

  const uploadAttachment = async (e) => {
    e.preventDefault()
    try {
      const formData = new FormData()
      Object.entries(attachmentForm).forEach(([key, value]) => formData.append(key, value))
      if (attachmentFile) formData.append('file', attachmentFile)
      await api.post('/ticket-attachments/', formData)
      setAttachmentForm(initialAttachment)
      setAttachmentFile(null)
      const input = document.getElementById('ticketAttachmentFile')
      if (input) input.value = ''
      await load()
      showMessage('Attachment uploaded.')
    } catch (err) {
      showError(err)
    }
  }

  const downloadAttachment = async (row) => {
    try {
      const res = await api.get(`/ticket-attachments/${row.id}/download/`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', row.file_name || `ticket-attachment-${row.id}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      showError(err)
    }
  }

  const supportUsers = employees.filter(item => ['OWNER', 'ADMIN', 'HR', 'IT'].includes(item.account_role))

  const ticketColumns = [
    { key: 'ticket_number', label: 'Ticket No' },
    { key: 'subject', label: 'Subject' },
    { key: 'requested_by_email', label: 'Employee' },
    { key: 'category_name', label: 'Category' },
    { key: 'priority', label: 'Priority' },
    { key: 'status', label: 'Status' },
    { key: 'assigned_to_email', label: 'Assigned To' },
    { key: 'is_overdue', label: 'Overdue', render: row => row.is_overdue ? 'Yes' : 'No' },
    {
      key: 'actions',
      label: 'Actions',
      render: row => (
        <div className="actions">
          <button onClick={() => addComment(row)}>Comment</button>
          {canManage && <button onClick={() => assignTicket(row)}>Assign</button>}
          {canManage && <button onClick={() => ticketAction(row, 'start')}>Start</button>}
          {canManage && <button onClick={() => pendingUser(row)}>Pending</button>}
          {canManage && <button onClick={() => resolveTicket(row)}>Resolve</button>}
          <button onClick={() => ticketAction(row, 'close', {}, 'Ticket closed.')}>Close</button>
          <button onClick={() => ticketAction(row, 'reopen', {}, 'Ticket reopened.')}>Reopen</button>
          <button className="dangerBtn" onClick={() => ticketAction(row, 'cancel', {}, 'Ticket cancelled.')}>Cancel</button>
        </div>
      )
    }
  ]

  return (
    <div>
      <PageHeader title="Helpdesk" subtitle="Employee support tickets, attachments, comments, assignment, and resolution workflow." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="statsGrid smallStats">
        <div className="stat"><span>Open</span><strong>{tickets.filter(item => item.status === 'OPEN').length}</strong></div>
        <div className="stat"><span>In Progress</span><strong>{tickets.filter(item => item.status === 'IN_PROGRESS').length}</strong></div>
        <div className="stat"><span>Pending User</span><strong>{tickets.filter(item => item.status === 'PENDING_USER').length}</strong></div>
        <div className="stat"><span>Resolved/Closed</span><strong>{tickets.filter(item => ['RESOLVED', 'CLOSED'].includes(item.status)).length}</strong></div>
      </div>

      {canManage && (
        <form className="inlineForm wideForm" onSubmit={createCategory}>
          <input placeholder="Category name" value={categoryForm.name} onChange={e => setCategoryForm({ ...categoryForm, name: e.target.value })} required />
          <input placeholder="Description" value={categoryForm.description} onChange={e => setCategoryForm({ ...categoryForm, description: e.target.value })} />
          <select value={categoryForm.default_assignee || ''} onChange={e => setCategoryForm({ ...categoryForm, default_assignee: e.target.value })}>
            <option value="">Default assignee</option>
            {supportUsers.map(item => <option key={item.user} value={item.user}>{item.user_email} - {item.account_role}</option>)}
          </select>
          <label className="checkLabel"><input type="checkbox" checked={categoryForm.is_active} onChange={e => setCategoryForm({ ...categoryForm, is_active: e.target.checked })} /> Active</label>
          <button>Create Category</button>
        </form>
      )}

      <form className="inlineForm wideForm" onSubmit={createTicket}>
        {canManage && (
          <select value={ticketForm.requested_by || ''} onChange={e => setTicketForm({ ...ticketForm, requested_by: e.target.value })}>
            <option value="">Requesting employee</option>
            {employees.map(item => <option key={item.id} value={item.id}>{item.employee_code} - {item.user_email}</option>)}
          </select>
        )}
        <select value={ticketForm.category || ''} onChange={e => setTicketForm({ ...ticketForm, category: e.target.value })}>
          <option value="">Category</option>
          {categories.filter(item => item.is_active).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <select value={ticketForm.priority} onChange={e => setTicketForm({ ...ticketForm, priority: e.target.value })}>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
          <option value="CRITICAL">Critical</option>
        </select>
        {canManage && (
          <select value={ticketForm.assigned_to || ''} onChange={e => setTicketForm({ ...ticketForm, assigned_to: e.target.value })}>
            <option value="">Assign to</option>
            {supportUsers.map(item => <option key={item.user} value={item.user}>{item.user_email} - {item.account_role}</option>)}
          </select>
        )}
        {canManage && <input type="datetime-local" value={ticketForm.due_at || ''} onChange={e => setTicketForm({ ...ticketForm, due_at: e.target.value })} />}
        <input placeholder="Subject" value={ticketForm.subject} onChange={e => setTicketForm({ ...ticketForm, subject: e.target.value })} required />
        <textarea placeholder="Describe the issue" value={ticketForm.description} onChange={e => setTicketForm({ ...ticketForm, description: e.target.value })} />
        <button>Create Ticket</button>
      </form>

      <DataTable columns={ticketColumns} rows={tickets} />

      <form className="inlineForm wideForm" onSubmit={uploadAttachment}>
        <select value={attachmentForm.ticket || ''} onChange={e => setAttachmentForm({ ...attachmentForm, ticket: e.target.value })} required>
          <option value="">Ticket</option>
          {tickets.map(item => <option key={item.id} value={item.id}>{item.ticket_number} - {item.subject}</option>)}
        </select>
        <input placeholder="Attachment title" value={attachmentForm.title} onChange={e => setAttachmentForm({ ...attachmentForm, title: e.target.value })} />
        <input placeholder="Notes" value={attachmentForm.notes} onChange={e => setAttachmentForm({ ...attachmentForm, notes: e.target.value })} />
        <input id="ticketAttachmentFile" type="file" onChange={e => setAttachmentFile(e.target.files[0])} required />
        <button>Upload Attachment</button>
      </form>

      <DataTable
        columns={[
          { key: 'ticket_number', label: 'Ticket' },
          { key: 'file_name', label: 'File' },
          { key: 'title', label: 'Title' },
          { key: 'file_size', label: 'Size' },
          { key: 'uploaded_by_email', label: 'Uploaded By' },
          { key: 'actions', label: 'Actions', render: row => <button onClick={() => downloadAttachment(row)}>Download</button> }
        ]}
        rows={attachments}
      />

      <DataTable
        columns={[
          { key: 'ticket_number', label: 'Ticket' },
          { key: 'author_email', label: 'Author' },
          { key: 'message', label: 'Comment' },
          { key: 'is_internal', label: 'Internal', render: row => row.is_internal ? 'Yes' : 'No' },
          { key: 'created_at', label: 'Created' }
        ]}
        rows={comments}
      />
    </div>
  )
}
