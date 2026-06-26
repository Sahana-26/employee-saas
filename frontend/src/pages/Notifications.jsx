import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'

export default function Notifications() {
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
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
    const [notificationRes, countRes] = await Promise.all([
      api.get('/notifications/'),
      api.get('/notifications/unread-count/')
    ])
    setNotifications(normalize(notificationRes.data))
    setUnreadCount(countRes.data.unread_count || 0)
  }

  useEffect(() => { load().catch(showError) }, [])

  const markRead = async (row) => {
    try {
      await api.post(`/notifications/${row.id}/mark-read/`)
      await load()
      showMessage('Notification marked as read.')
    } catch (err) {
      showError(err)
    }
  }

  const markUnread = async (row) => {
    try {
      await api.post(`/notifications/${row.id}/mark-unread/`)
      await load()
      showMessage('Notification marked as unread.')
    } catch (err) {
      showError(err)
    }
  }

  const markAllRead = async () => {
    try {
      const res = await api.post('/notifications/mark-all-read/')
      await load()
      showMessage(res.data.detail || 'All notifications marked as read.')
    } catch (err) {
      showError(err)
    }
  }

  return (
    <section>
      <PageHeader title="Notifications" subtitle="View workflow alerts for leaves, profile requests, payroll, expenses, and HR actions." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="statsGrid smallStats">
        <div className="stat"><span>Unread</span><strong>{unreadCount}</strong></div>
        <div className="stat"><span>Total Loaded</span><strong>{notifications.length}</strong></div>
      </div>

      <div className="infoCard">
        <button onClick={markAllRead}>Mark All Read</button>
      </div>

      <DataTable columns={[
        { key: 'title', label: 'Title' },
        { key: 'message', label: 'Message' },
        { key: 'notification_type', label: 'Type' },
        { key: 'related_module', label: 'Module' },
        { key: 'is_read', label: 'Status', render: row => row.is_read ? 'Read' : 'Unread' },
        { key: 'created_at', label: 'Created', render: row => row.created_at ? new Date(row.created_at).toLocaleString() : '' },
        { key: 'actions', label: 'Actions', render: row => (
          <div className="actions">
            {row.action_url && <button onClick={() => window.location.href = row.action_url}>Open</button>}
            {!row.is_read && <button onClick={() => markRead(row)}>Read</button>}
            {row.is_read && <button onClick={() => markUnread(row)}>Unread</button>}
          </div>
        ) }
      ]} rows={notifications} />
    </section>
  )
}
