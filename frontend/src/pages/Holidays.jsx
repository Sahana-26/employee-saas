import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'

const initialForm = {
  name: '',
  date: '',
  holiday_type: 'PUBLIC',
  is_optional: false,
  description: ''
}

export default function Holidays() {
  const [rows, setRows] = useState([])
  const [form, setForm] = useState(initialForm)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const load = async () => {
    const res = await api.get('/holidays/')
    setRows(res.data.results || res.data)
  }

  useEffect(() => { load().catch(() => {}) }, [])

  const updateForm = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.post('/holidays/', form)
      setForm(initialForm)
      setMessage('Holiday created successfully.')
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to create holiday'))
    }
  }

  return (
    <section>
      <PageHeader title="Holiday Calendar" subtitle="Manage public, company, festival, and optional holidays." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      <form className="inlineForm wideForm" onSubmit={submit}>
        <input placeholder="Holiday name" value={form.name} onChange={e => updateForm('name', e.target.value)} required />
        <input type="date" value={form.date} onChange={e => updateForm('date', e.target.value)} required />
        <select value={form.holiday_type} onChange={e => updateForm('holiday_type', e.target.value)}>
          <option value="PUBLIC">Public Holiday</option>
          <option value="COMPANY">Company Holiday</option>
          <option value="FESTIVAL">Festival</option>
          <option value="OPTIONAL">Optional Holiday</option>
        </select>
        <input placeholder="Description" value={form.description} onChange={e => updateForm('description', e.target.value)} />
        <label className="checkLabel"><input type="checkbox" checked={form.is_optional} onChange={e => updateForm('is_optional', e.target.checked)} /> Optional</label>
        <button>Add Holiday</button>
      </form>
      <DataTable columns={[
        { key: 'name', label: 'Holiday' },
        { key: 'date', label: 'Date' },
        { key: 'holiday_type', label: 'Type' },
        { key: 'is_optional', label: 'Optional', render: row => row.is_optional ? 'Yes' : 'No' },
        { key: 'description', label: 'Description' }
      ]} rows={rows} />
    </section>
  )
}
