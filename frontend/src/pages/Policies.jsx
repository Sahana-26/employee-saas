import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { HR_ROLES, hasRole } from '../utils/roles.js'

const roleOptions = ['OWNER', 'ADMIN', 'HR', 'MANAGER', 'EMPLOYEE', 'PAYROLL', 'VIEWER']
const categoryOptions = ['HR', 'ATTENDANCE', 'LEAVE', 'PAYROLL', 'EXPENSE', 'IT', 'SECURITY', 'CONDUCT', 'OTHER']

export default function Policies() {
  const { user } = useAuth()
  const [policies, setPolicies] = useState([])
  const [pending, setPending] = useState([])
  const [acknowledgements, setAcknowledgements] = useState([])
  const [selectedPolicy, setSelectedPolicy] = useState('')
  const [policyDocument, setPolicyDocument] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    title: '',
    code: '',
    version: '1.0',
    category: 'HR',
    summary: '',
    content: '',
    audience_roles: [],
    requires_acknowledgement: true,
    is_published: false
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
    const policyRes = await api.get('/policies/')
    setPolicies(normalize(policyRes.data))
    if (!canManage) {
      const pendingRes = await api.get('/policies/pending-acknowledgements/')
      setPending(normalize(pendingRes.data))
    } else {
      setPending([])
    }
  }

  useEffect(() => { load().catch(showError) }, [canManage])

  const toggleRole = (role) => {
    setForm(current => {
      const roles = current.audience_roles.includes(role)
        ? current.audience_roles.filter(item => item !== role)
        : [...current.audience_roles, role]
      return { ...current, audience_roles: roles }
    })
  }

  const createPolicy = async (e) => {
    e.preventDefault()
    try {
      const formData = new FormData()
      Object.entries(form).forEach(([key, value]) => {
        if (key === 'audience_roles') {
          formData.append(key, JSON.stringify(value))
        } else {
          formData.append(key, value)
        }
      })
      if (policyDocument) formData.append('document', policyDocument)
      await api.post('/policies/', formData)
      setForm({ title: '', code: '', version: '1.0', category: 'HR', summary: '', content: '', audience_roles: [], requires_acknowledgement: true, is_published: false })
      setPolicyDocument(null)
      const input = window.document.getElementById('policyDocument')
      if (input) input.value = ''
      await load()
      showMessage('Policy created.')
    } catch (err) {
      showError(err)
    }
  }

  const policyAction = async (row, actionName, successText) => {
    try {
      const res = await api.post(`/policies/${row.id}/${actionName}/`)
      await load()
      showMessage(res.data.detail || successText)
    } catch (err) {
      showError(err)
    }
  }

  const downloadDocument = async (row) => {
    try {
      const res = await api.get(`/policies/${row.id}/download-document/`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = window.document.createElement('a')
      link.href = url
      link.setAttribute('download', row.document_file_name || `policy-${row.id}`)
      window.document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      showError(err)
    }
  }

  const loadAcknowledgements = async (row) => {
    try {
      const res = await api.get(`/policies/${row.id}/acknowledgements/`)
      setAcknowledgements(normalize(res.data))
      setSelectedPolicy(`${row.title} v${row.version}`)
      showMessage('Acknowledgement list loaded.')
    } catch (err) {
      showError(err)
    }
  }

  return (
    <section>
      <PageHeader title="Company Policies" subtitle="Create policies, publish documents, and track employee acknowledgement." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {pending.length > 0 && (
        <div className="infoCard">
          <strong>Pending acknowledgement:</strong> You have {pending.length} policy document(s) waiting for your acknowledgement.
        </div>
      )}

      {canManage && (
        <>
          <h3>Create Policy</h3>
          <form className="inlineForm wideForm announcementForm" onSubmit={createPolicy}>
            <input placeholder="Policy title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} required />
            <input placeholder="Policy code, e.g. HR-001" value={form.code} onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })} required />
            <input placeholder="Version" value={form.version} onChange={e => setForm({ ...form, version: e.target.value })} required />
            <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
              {categoryOptions.map(category => <option key={category} value={category}>{category}</option>)}
            </select>
            <textarea placeholder="Summary" value={form.summary} onChange={e => setForm({ ...form, summary: e.target.value })} />
            <textarea placeholder="Full policy content" value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} />
            <input id="policyDocument" type="file" onChange={e => setPolicyDocument(e.target.files?.[0] || null)} />
            <label className="checkLabel"><input type="checkbox" checked={form.requires_acknowledgement} onChange={e => setForm({ ...form, requires_acknowledgement: e.target.checked })} /> Requires acknowledgement</label>
            <label className="checkLabel"><input type="checkbox" checked={form.is_published} onChange={e => setForm({ ...form, is_published: e.target.checked })} /> Publish immediately</label>
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
            <button>Create Policy</button>
          </form>
        </>
      )}

      <h3>Policy Library</h3>
      <DataTable columns={[
        { key: 'code', label: 'Code' },
        { key: 'title', label: 'Title' },
        { key: 'version', label: 'Version' },
        { key: 'category', label: 'Category' },
        { key: 'audience_roles', label: 'Audience', render: row => row.audience_roles?.length ? row.audience_roles.join(', ') : 'All' },
        { key: 'requires_acknowledgement', label: 'Ack Required', render: row => row.requires_acknowledgement ? 'Yes' : 'No' },
        { key: 'is_published', label: 'Published', render: row => row.is_published ? 'Yes' : 'No' },
        { key: 'is_acknowledged_by_me', label: 'My Status', render: row => row.requires_acknowledgement ? (row.is_acknowledged_by_me ? 'Acknowledged' : 'Pending') : 'Not required' },
        { key: 'acknowledgement_count', label: 'Ack Count' },
        { key: 'actions', label: 'Actions', render: row => (
          <div className="actions">
            {row.has_document && <button onClick={() => downloadDocument(row)}>Document</button>}
            {row.requires_acknowledgement && row.is_published && !row.is_acknowledged_by_me && <button onClick={() => policyAction(row, 'acknowledge', 'Policy acknowledged.')}>Acknowledge</button>}
            {canManage && !row.is_published && <button onClick={() => policyAction(row, 'publish', 'Policy published.')}>Publish</button>}
            {canManage && row.is_published && <button className="dangerBtn" onClick={() => policyAction(row, 'archive', 'Policy archived.')}>Archive</button>}
            {canManage && <button onClick={() => loadAcknowledgements(row)}>Acknowledgements</button>}
          </div>
        ) }
      ]} rows={policies} />

      {canManage && selectedPolicy && (
        <>
          <h3>Acknowledgements - {selectedPolicy}</h3>
          <DataTable columns={[
            { key: 'user_email', label: 'Employee' },
            { key: 'acknowledged_at', label: 'Acknowledged At' },
            { key: 'ip_address', label: 'IP Address' }
          ]} rows={acknowledgements} />
        </>
      )}
    </section>
  )
}
