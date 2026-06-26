import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'

export default function Departments() {
  const [rows, setRows] = useState([])
  const [form, setForm] = useState({ name: '', description: '' })

  const load = async () => {
    const res = await api.get('/departments/')
    setRows(res.data.results || res.data)
  }

  useEffect(() => { load() }, [])

  const submit = async (e) => {
    e.preventDefault()
    await api.post('/departments/', form)
    setForm({ name: '', description: '' })
    load()
  }

  return (
    <section>
      <PageHeader title="Departments" subtitle="Manage company departments" />
      <form className="inlineForm" onSubmit={submit}>
        <input placeholder="Department name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
        <input placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
        <button>Add</button>
      </form>
      <DataTable columns={[{ key: 'name', label: 'Name' }, { key: 'description', label: 'Description' }]} rows={rows} />
    </section>
  )
}
