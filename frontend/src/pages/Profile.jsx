import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { HR_ROLES, hasRole } from '../utils/roles.js'

const emptyRequest = {
  bank_name: '',
  bank_account_number: '',
  bank_ifsc: '',
  bank_branch: '',
  tax_id: '',
  date_of_birth: '',
  gender: '',
  blood_group: '',
  marital_status: '',
  reason: ''
}

function valueOrBlank(value) {
  return value || ''
}

function formatRequestedData(data) {
  if (!data) return '-'
  return Object.entries(data).map(([key, value]) => `${key}: ${value}`).join(' | ')
}

export default function Profile() {
  const { user } = useAuth()
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState({})
  const [requestForm, setRequestForm] = useState(emptyRequest)
  const [requests, setRequests] = useState([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const normalize = data => data.results || data
  const canReview = hasRole(user, HR_ROLES)

  const load = async () => {
    const requestRes = await api.get('/profile-change-requests/')
    setRequests(normalize(requestRes.data))
    try {
      const profileRes = await api.get('/profile/me/')
      setProfile(profileRes.data)
      setForm({
        first_name: valueOrBlank(profileRes.data.first_name),
        last_name: valueOrBlank(profileRes.data.last_name),
        phone: valueOrBlank(profileRes.data.phone),
        personal_email: valueOrBlank(profileRes.data.personal_email),
        address: valueOrBlank(profileRes.data.address),
        permanent_address: valueOrBlank(profileRes.data.permanent_address),
        emergency_contact_name: valueOrBlank(profileRes.data.emergency_contact_name),
        emergency_contact_phone: valueOrBlank(profileRes.data.emergency_contact_phone),
        emergency_contact_relation: valueOrBlank(profileRes.data.emergency_contact_relation)
      })
    } catch {
      setProfile(null)
    }
  }

  useEffect(() => { load().catch(() => {}) }, [])

  const updateForm = (key, value) => setForm(prev => ({ ...prev, [key]: value }))
  const updateRequest = (key, value) => setRequestForm(prev => ({ ...prev, [key]: value }))

  const saveProfile = async (e) => {
    e.preventDefault()
    setMessage('')
    setError('')
    try {
      const res = await api.patch('/profile/me/', form)
      setProfile(res.data)
      setMessage('Profile updated successfully.')
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to update profile'))
    }
  }

  const submitRequest = async (e) => {
    e.preventDefault()
    setMessage('')
    setError('')
    const requestedData = {}
    Object.entries(requestForm).forEach(([key, value]) => {
      if (key !== 'reason' && value !== '') requestedData[key] = value
    })
    if (!Object.keys(requestedData).length) {
      setError('Enter at least one field for HR approval.')
      return
    }
    try {
      await api.post('/profile-change-requests/', {
        requested_data: requestedData,
        reason: requestForm.reason
      })
      setRequestForm(emptyRequest)
      setMessage('Profile change request submitted for HR review.')
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to submit profile change request'))
    }
  }

  const reviewRequest = async (row, action) => {
    setMessage('')
    setError('')
    try {
      await api.post(`/profile-change-requests/${row.id}/${action}/`, { review_note: action === 'approve' ? 'Approved' : 'Rejected' })
      setMessage(`Profile request ${action === 'approve' ? 'approved' : 'rejected'} successfully.`)
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to review profile request'))
    }
  }

  return (
    <section>
      <PageHeader title="My Profile" subtitle="Employees can maintain profile details and submit verified changes for HR approval." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {!profile && <div className="infoCard">No employee profile is linked to this login. HR/Admin users can still review profile change requests below.</div>}

      {profile && (
        <div className="profileGrid">
          <div className="settingsCard">
            <h3>Profile Summary</h3>
            <p><strong>{profile.full_name}</strong></p>
            <p>{profile.email}</p>
            <p>Employee Code: {profile.employee_code}</p>
            <p>Department: {profile.department_name || '-'}</p>
            <p>Designation: {profile.designation || '-'}</p>
            <p>Manager: {profile.manager_name || '-'}</p>
            <p>Completion: <strong>{profile.profile_completion_percent}%</strong></p>
          </div>

          <form className="settingsCard profileForm" onSubmit={saveProfile}>
            <h3>Editable Information</h3>
            <input placeholder="First name" value={form.first_name || ''} onChange={e => updateForm('first_name', e.target.value)} />
            <input placeholder="Last name" value={form.last_name || ''} onChange={e => updateForm('last_name', e.target.value)} />
            <input placeholder="Phone" value={form.phone || ''} onChange={e => updateForm('phone', e.target.value)} />
            <input placeholder="Personal email" value={form.personal_email || ''} onChange={e => updateForm('personal_email', e.target.value)} />
            <input placeholder="Emergency contact name" value={form.emergency_contact_name || ''} onChange={e => updateForm('emergency_contact_name', e.target.value)} />
            <input placeholder="Emergency contact phone" value={form.emergency_contact_phone || ''} onChange={e => updateForm('emergency_contact_phone', e.target.value)} />
            <input placeholder="Emergency contact relation" value={form.emergency_contact_relation || ''} onChange={e => updateForm('emergency_contact_relation', e.target.value)} />
            <textarea placeholder="Current address" value={form.address || ''} onChange={e => updateForm('address', e.target.value)} />
            <textarea placeholder="Permanent address" value={form.permanent_address || ''} onChange={e => updateForm('permanent_address', e.target.value)} />
            <button>Save Profile</button>
          </form>
        </div>
      )}

      {profile && (
        <>
          <PageHeader title="Verified Change Request" subtitle="Use this for bank, tax, date of birth, and other details that HR should review." />
          <form className="inlineForm wideForm" onSubmit={submitRequest}>
            <input placeholder="Bank name" value={requestForm.bank_name} onChange={e => updateRequest('bank_name', e.target.value)} />
            <input placeholder="Bank account number" value={requestForm.bank_account_number} onChange={e => updateRequest('bank_account_number', e.target.value)} />
            <input placeholder="IFSC" value={requestForm.bank_ifsc} onChange={e => updateRequest('bank_ifsc', e.target.value)} />
            <input placeholder="Bank branch" value={requestForm.bank_branch} onChange={e => updateRequest('bank_branch', e.target.value)} />
            <input placeholder="Tax ID / PAN" value={requestForm.tax_id} onChange={e => updateRequest('tax_id', e.target.value)} />
            <input type="date" value={requestForm.date_of_birth} onChange={e => updateRequest('date_of_birth', e.target.value)} />
            <input placeholder="Gender" value={requestForm.gender} onChange={e => updateRequest('gender', e.target.value)} />
            <input placeholder="Blood group" value={requestForm.blood_group} onChange={e => updateRequest('blood_group', e.target.value)} />
            <input placeholder="Marital status" value={requestForm.marital_status} onChange={e => updateRequest('marital_status', e.target.value)} />
            <input placeholder="Reason" value={requestForm.reason} onChange={e => updateRequest('reason', e.target.value)} />
            <button>Submit for Approval</button>
          </form>
        </>
      )}

      <PageHeader title={canReview ? 'Profile Change Requests' : 'My Change Requests'} subtitle={canReview ? 'HR/Admin can approve or reject submitted profile updates.' : 'Track your submitted profile updates.'} />
      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'employee_code', label: 'Code' },
        { key: 'requested_data', label: 'Requested Data', render: row => formatRequestedData(row.requested_data) },
        { key: 'reason', label: 'Reason' },
        { key: 'status', label: 'Status' },
        { key: 'reviewed_by_email', label: 'Reviewed By', render: row => row.reviewed_by_email || '-' },
        { key: 'actions', label: 'Actions', render: row => canReview && row.status === 'PENDING' ? (
          <div className="actions">
            <button type="button" onClick={() => reviewRequest(row, 'approve')}>Approve</button>
            <button type="button" className="dangerBtn" onClick={() => reviewRequest(row, 'reject')}>Reject</button>
          </div>
        ) : '-' }
      ]} rows={requests} />
    </section>
  )
}
