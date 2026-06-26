import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { HR_ROLES, hasRole } from '../utils/roles.js'

const initialTemplate = {
  code: '', name: '', category: 'OTHER', version: '1.0', description: '',
  content: '<h2>{{ organization.name }}</h2><p>Date: {{ today }}</p><p>Dear {{ employee.full_name }},</p><p>Your letter content goes here.</p><p>Regards,<br>{{ custom.signatory_name }}</p>',
  requires_approval: true, is_active: true
}

const initialLetter = { employee: '', template: '', letter_number: '', title: '', category: 'OTHER', custom_variables_text: '{\n  "signatory_name": "HR Manager",\n  "signatory_designation": "HR"\n}', remarks: '' }

export default function Letters() {
  const { user } = useAuth()
  const canManage = hasRole(user, HR_ROLES)
  const [templates, setTemplates] = useState([])
  const [letters, setLetters] = useState([])
  const [employees, setEmployees] = useState([])
  const [variables, setVariables] = useState([])
  const [templateForm, setTemplateForm] = useState(initialTemplate)
  const [letterForm, setLetterForm] = useState(initialLetter)
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
    const requests = [api.get('/hr-letter-templates/'), api.get('/generated-letters/')]
    if (canManage) requests.push(api.get('/employees/'), api.get('/hr-letter-templates/variables/'))
    const responses = await Promise.all(requests)
    setTemplates(normalize(responses[0].data))
    setLetters(normalize(responses[1].data))
    if (canManage) {
      setEmployees(normalize(responses[2].data))
      setVariables(responses[3].data.variables || [])
    }
  }

  useEffect(() => { load().catch(showError) }, [canManage])

  const createTemplate = async (e) => {
    e.preventDefault()
    try {
      await api.post('/hr-letter-templates/', { ...templateForm, available_variables: variables })
      setTemplateForm(initialTemplate)
      await load()
      showMessage('Letter template created.')
    } catch (err) {
      showError(err)
    }
  }

  const createLetter = async (e) => {
    e.preventDefault()
    try {
      const template = templates.find(item => String(item.id) === String(letterForm.template))
      let customVariables = {}
      if (letterForm.custom_variables_text?.trim()) customVariables = JSON.parse(letterForm.custom_variables_text)
      await api.post('/generated-letters/', {
        employee: letterForm.employee,
        template: letterForm.template || null,
        letter_number: letterForm.letter_number || '',
        title: letterForm.title || template?.name || 'HR Letter',
        category: template?.category || letterForm.category,
        custom_variables: customVariables,
        remarks: letterForm.remarks
      })
      setLetterForm(initialLetter)
      await load()
      showMessage('Letter generated and stored in PostgreSQL.')
    } catch (err) {
      showError(err)
    }
  }

  const templateAction = async (row, action, success) => {
    try {
      await api.post(`/hr-letter-templates/${row.id}/${action}/`)
      await load()
      showMessage(success)
    } catch (err) {
      showError(err)
    }
  }

  const letterAction = async (row, action, payload = {}, success = 'Letter updated.') => {
    try {
      await api.post(`/generated-letters/${row.id}/${action}/`, payload)
      await load()
      showMessage(success)
    } catch (err) {
      showError(err)
    }
  }

  const rejectLetter = async (row) => {
    const reason = window.prompt('Rejection reason', row.rejection_reason || '')
    if (reason === null) return
    await letterAction(row, 'reject', { rejection_reason: reason }, 'Letter rejected.')
  }

  const cancelLetter = async (row) => {
    const note = window.prompt('Cancellation note', '')
    if (note === null) return
    await letterAction(row, 'cancel', { note }, 'Letter cancelled.')
  }

  const downloadLetter = async (row) => {
    try {
      const response = await api.get(`/generated-letters/${row.id}/download/`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([response.data], { type: row.document_content_type || 'text/html' }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', row.document_filename || `${row.letter_number || row.id}.html`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      showError(err)
    }
  }

  const selectedTemplate = templates.find(item => String(item.id) === String(letterForm.template))

  return (
    <div>
      <PageHeader title="HR Letters" subtitle="Create HR letter templates, generate employee letters, approve, sign, issue, and download PostgreSQL-stored documents." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="statsGrid smallStats">
        <div className="stat"><span>Templates</span><strong>{templates.length}</strong></div>
        <div className="stat"><span>Generated</span><strong>{letters.length}</strong></div>
        <div className="stat"><span>Pending Approval</span><strong>{letters.filter(item => ['DRAFT', 'GENERATED'].includes(item.status)).length}</strong></div>
        <div className="stat"><span>Issued</span><strong>{letters.filter(item => item.status === 'ISSUED').length}</strong></div>
      </div>

      {canManage && (
        <form className="inlineForm wideForm letterForm" onSubmit={createTemplate}>
          <input placeholder="Template code" value={templateForm.code} onChange={e => setTemplateForm({ ...templateForm, code: e.target.value })} required />
          <input placeholder="Template name" value={templateForm.name} onChange={e => setTemplateForm({ ...templateForm, name: e.target.value })} required />
          <select value={templateForm.category} onChange={e => setTemplateForm({ ...templateForm, category: e.target.value })}>
            <option value="OFFER">Offer</option>
            <option value="APPOINTMENT">Appointment</option>
            <option value="CONFIRMATION">Confirmation</option>
            <option value="INCREMENT">Increment</option>
            <option value="SALARY">Salary Certificate</option>
            <option value="EXPERIENCE">Experience</option>
            <option value="RELIEVING">Relieving</option>
            <option value="WARNING">Warning</option>
            <option value="NOC">NOC</option>
            <option value="OTHER">Other</option>
          </select>
          <input placeholder="Version" value={templateForm.version} onChange={e => setTemplateForm({ ...templateForm, version: e.target.value })} />
          <label className="checkLabel"><input type="checkbox" checked={templateForm.requires_approval} onChange={e => setTemplateForm({ ...templateForm, requires_approval: e.target.checked })} /> Requires approval</label>
          <textarea placeholder="Description" value={templateForm.description} onChange={e => setTemplateForm({ ...templateForm, description: e.target.value })} />
          <textarea className="largeTextarea" placeholder="HTML/Text template content" value={templateForm.content} onChange={e => setTemplateForm({ ...templateForm, content: e.target.value })} required />
          <div className="infoCard variableHelp">
            <strong>Common variables:</strong> {variables.slice(0, 12).map(item => <code key={item}>{'{{ ' + item + ' }}'}</code>)}
          </div>
          <button>Create Template</button>
        </form>
      )}

      <DataTable
        columns={[
          { key: 'code', label: 'Code' },
          { key: 'name', label: 'Template' },
          { key: 'category', label: 'Category' },
          { key: 'version', label: 'Version' },
          { key: 'requires_approval', label: 'Approval', render: row => row.requires_approval ? 'Required' : 'Auto-approved' },
          { key: 'is_active', label: 'Active', render: row => row.is_active ? 'Yes' : 'No' },
          { key: 'actions', label: 'Actions', render: row => canManage ? <div className="actions"><button onClick={() => templateAction(row, 'activate', 'Template activated.')}>Activate</button><button className="dangerBtn" onClick={() => templateAction(row, 'archive', 'Template archived.')}>Archive</button></div> : '-' }
        ]}
        rows={templates}
      />

      {canManage && (
        <form className="inlineForm wideForm letterForm" onSubmit={createLetter}>
          <select value={letterForm.employee || ''} onChange={e => setLetterForm({ ...letterForm, employee: e.target.value })} required>
            <option value="">Employee</option>
            {employees.map(item => <option key={item.id} value={item.id}>{item.employee_code} - {item.user_email}</option>)}
          </select>
          <select value={letterForm.template || ''} onChange={e => setLetterForm({ ...letterForm, template: e.target.value, title: templates.find(t => String(t.id) === e.target.value)?.name || letterForm.title })} required>
            <option value="">Template</option>
            {templates.filter(item => item.is_active).map(item => <option key={item.id} value={item.id}>{item.code} - {item.name}</option>)}
          </select>
          <input placeholder="Letter number auto if blank" value={letterForm.letter_number} onChange={e => setLetterForm({ ...letterForm, letter_number: e.target.value })} />
          <input placeholder="Letter title" value={letterForm.title} onChange={e => setLetterForm({ ...letterForm, title: e.target.value })} />
          <select value={selectedTemplate?.category || letterForm.category} onChange={e => setLetterForm({ ...letterForm, category: e.target.value })} disabled={Boolean(selectedTemplate)}>
            <option value="OFFER">Offer</option>
            <option value="APPOINTMENT">Appointment</option>
            <option value="CONFIRMATION">Confirmation</option>
            <option value="INCREMENT">Increment</option>
            <option value="SALARY">Salary Certificate</option>
            <option value="EXPERIENCE">Experience</option>
            <option value="RELIEVING">Relieving</option>
            <option value="WARNING">Warning</option>
            <option value="NOC">NOC</option>
            <option value="OTHER">Other</option>
          </select>
          <textarea className="largeTextarea" placeholder="Custom variables JSON" value={letterForm.custom_variables_text} onChange={e => setLetterForm({ ...letterForm, custom_variables_text: e.target.value })} />
          <textarea placeholder="Remarks" value={letterForm.remarks} onChange={e => setLetterForm({ ...letterForm, remarks: e.target.value })} />
          <button>Generate Letter</button>
        </form>
      )}

      <DataTable
        columns={[
          { key: 'letter_number', label: 'Letter No.' },
          { key: 'title', label: 'Title' },
          { key: 'employee_code', label: 'Employee Code' },
          { key: 'employee_email', label: 'Employee' },
          { key: 'category', label: 'Category' },
          { key: 'status', label: 'Status' },
          { key: 'document_size', label: 'Size' },
          { key: 'actions', label: 'Actions', render: row => <div className="actions">
            {canManage && <button onClick={() => letterAction(row, 'generate', {}, 'Letter regenerated.')}>Generate</button>}
            {canManage && <button onClick={() => letterAction(row, 'approve', {}, 'Letter approved.')}>Approve</button>}
            {canManage && <button onClick={() => rejectLetter(row)}>Reject</button>}
            {canManage && <button onClick={() => letterAction(row, 'sign', {}, 'Letter signed.')}>Sign</button>}
            {canManage && <button onClick={() => letterAction(row, 'issue', {}, 'Letter issued.')}>Issue</button>}
            {row.can_download && <button onClick={() => downloadLetter(row)}>Download</button>}
            {canManage && <button className="dangerBtn" onClick={() => cancelLetter(row)}>Cancel</button>}
          </div> }
        ]}
        rows={letters}
      />
    </div>
  )
}
