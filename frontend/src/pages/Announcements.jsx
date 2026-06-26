import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { HR_ROLES, hasRole } from '../utils/roles.js'

const roleOptions = ['OWNER', 'ADMIN', 'HR', 'MANAGER', 'EMPLOYEE', 'PAYROLL', 'VIEWER']

export default function Announcements() {
  const { user } = useAuth()
  const [announcements, setAnnouncements] = useState([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    title: '',
    message: '',
    audience_roles: [],
    starts_at: '',
    expires_at: '',
    is_published: true
  })

  const canManage = hasRole(user, HR_ROLES)
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
    const res = await api.get('/announcements/')
    setAnnouncements(normalize(res.data))
  }

  useEffect(() => { load().catch(showError) }, [])

  const toggleRole = (role) => {
    setForm(current => {
      const roles = current.audience_roles.includes(role)
        ? current.audience_roles.filter(item => item !== role)
        : [...current.audience_roles, role]
      return { ...current, audience_roles: roles }
    })
  }

  const createAnnouncement = async (e) => {
    e.preventDefault()
    try {
      const payload = {
        ...form,
        starts_at: form.starts_at || null,
        expires_at: form.expires_at || null
      }
      await api.post('/announcements/', payload)
      setForm({ title: '', message: '', audience_roles: [], starts_at: '', expires_at: '', is_published: true })
      await load()
      showMessage('Announcement created.')
    } catch (err) {
      showError(err)
    }
  }

  const action = async (row, endpoint, label) => {
    try {
      await api.post(`/announcements/${row.id}/${endpoint}/`)
      await load()
      showMessage(label)
    } catch (err) {
      showError(err)
    }
  }

  return (
    <section>
      <PageHeader title="Announcements" subtitle="Publish internal announcements for all employees or selected roles." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {canManage && (
        <>
          <h3>Create Announcement</h3>
          <form className="inlineForm wideForm announcementForm" onSubmit={createAnnouncement}>
            <input placeholder="Title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} required />
            <textarea placeholder="Message" value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} required />
            <label className="checkLabel"><input type="checkbox" checked={form.is_published} onChange={e => setForm({ ...form, is_published: e.target.checked })} /> Published</label>
            <input type="datetime-local" value={form.starts_at} onChange={e => setForm({ ...form, starts_at: e.target.value })} />
            <input type="datetime-local" value={form.expires_at} onChange={e => setForm({ ...form, expires_at: e.target.value })} />
            <div className="rolePicker">
              <strong>Audience roles</strong>
              <small>Leave all unchecked to show to everyone.</small>
              <div>
                {roleOptions.map(role => (
                  <label key={role} className="checkLabel">
                    <input type="checkbox" checked={form.audience_roles.includes(role)} onChange={() => toggleRole(role)} /> {role}
                  </label>
                ))}
              </div>
            </div>
            <button>Create Announcement</button>
          </form>
        </>
      )}

      <DataTable columns={[
        { key: 'title', label: 'Title' },
        { key: 'message', label: 'Message' },
        { key: 'audience_roles', label: 'Audience', render: row => row.audience_roles?.length ? row.audience_roles.join(', ') : 'All' },
        { key: 'is_published', label: 'Published', render: row => row.is_published ? 'Yes' : 'No' },
        { key: 'is_active', label: 'Active Now', render: row => row.is_active ? 'Yes' : 'No' },
        { key: 'is_read_by_me', label: 'My Status', render: row => row.is_read_by_me ? 'Read' : 'Unread' },
        { key: 'read_count', label: 'Reads' },
        { key: 'actions', label: 'Actions', render: row => (
          <div className="actions">
            {!row.is_read_by_me && <button onClick={() => action(row, 'mark-read', 'Announcement marked as read.')}>Read</button>}
            {canManage && !row.is_published && <button onClick={() => action(row, 'publish', 'Announcement published.')}>Publish</button>}
            {canManage && row.is_published && <button className="dangerBtn" onClick={() => action(row, 'archive', 'Announcement archived.')}>Archive</button>}
          </div>
        ) }
      ]} rows={announcements} />
    </section>
  )
}
