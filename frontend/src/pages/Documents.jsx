import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'

const categories = [
  ['ID', 'Identity'],
  ['CONTRACT', 'Contract'],
  ['CERTIFICATE', 'Certificate'],
  ['PAYSLIP', 'Payslip'],
  ['OTHER', 'Other']
]

export default function Documents() {
  const [rows, setRows] = useState([])
  const [employees, setEmployees] = useState([])
  const [form, setForm] = useState({ employee: '', title: '', category: 'OTHER', notes: '', file: null })
  const [message, setMessage] = useState('')

  const load = async () => {
    const [docRes, empRes] = await Promise.all([
      api.get('/documents/'),
      api.get('/employees/')
    ])
    setRows(docRes.data.results || docRes.data)
    setEmployees(empRes.data.results || empRes.data)
  }

  useEffect(() => { load() }, [])

  const submit = async (e) => {
    e.preventDefault()
    setMessage('')
    const payload = new FormData()
    payload.append('employee', form.employee)
    payload.append('title', form.title)
    payload.append('category', form.category)
    payload.append('notes', form.notes)
    payload.append('file', form.file)
    await api.post('/documents/', payload, { headers: { 'Content-Type': 'multipart/form-data' } })
    setForm({ employee: '', title: '', category: 'OTHER', notes: '', file: null })
    e.target.reset()
    setMessage('Document uploaded and stored in PostgreSQL.')
    load()
  }

  const download = async (row) => {
    const res = await api.get(`/documents/${row.id}/download/`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data], { type: row.content_type }))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', row.file_name)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  return (
    <section>
      <PageHeader title="Documents" subtitle="Upload employee documents directly into PostgreSQL" />
      <form className="inlineForm" onSubmit={submit}>
        <select required value={form.employee} onChange={e => setForm({ ...form, employee: e.target.value })}>
          <option value="">Employee</option>
          {employees.map(e => <option key={e.id} value={e.id}>{e.full_name}</option>)}
        </select>
        <input required placeholder="Title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
        <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
          {categories.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <input placeholder="Notes" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
        <input required type="file" onChange={e => setForm({ ...form, file: e.target.files[0] })} />
        <button>Upload</button>
      </form>
      {message && <p className="success">{message}</p>}
      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'title', label: 'Title' },
        { key: 'category', label: 'Category' },
        { key: 'file_name', label: 'File' },
        { key: 'size', label: 'Size' },
        { key: 'created_at', label: 'Uploaded' },
        { key: 'download', label: 'Action', render: row => <button onClick={() => download(row)}>Download</button> }
      ]} rows={rows} />
    </section>
  )
}
