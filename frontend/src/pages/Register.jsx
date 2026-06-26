import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client.js'

export default function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ organization_name: '', first_name: '', last_name: '', email: '', password: '' })
  const [error, setError] = useState('')

  const update = (key, value) => setForm({ ...form, [key]: value })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/auth/register-organization/', form)
      navigate('/login')
    } catch {
      setError('Unable to create workspace')
    }
  }

  return (
    <div className="authPage">
      <form className="authCard" onSubmit={submit}>
        <h1>Create Workspace</h1>
        <input placeholder="Company name" value={form.organization_name} onChange={e => update('organization_name', e.target.value)} />
        <input placeholder="First name" value={form.first_name} onChange={e => update('first_name', e.target.value)} />
        <input placeholder="Last name" value={form.last_name} onChange={e => update('last_name', e.target.value)} />
        <input placeholder="Email" value={form.email} onChange={e => update('email', e.target.value)} />
        <input placeholder="Password" type="password" value={form.password} onChange={e => update('password', e.target.value)} />
        {error && <div className="error">{error}</div>}
        <button>Create</button>
        <p>Already have an account? <Link to="/login">Login</Link></p>
      </form>
    </div>
  )
}
