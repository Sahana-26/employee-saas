import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { HR_ROLES, hasRole } from '../utils/roles.js'

const initialJob = {
  job_code: '', title: '', department: '', hiring_manager: '', employment_type: 'FULL_TIME', work_mode: 'OFFICE',
  location: '', openings_count: 1, min_experience: 0, max_experience: 0, salary_min: 0, salary_max: 0,
  description: '', requirements: '', target_start_date: ''
}

const initialCandidate = {
  job_opening: '', first_name: '', last_name: '', email: '', phone: '', source: 'OTHER', current_company: '',
  current_designation: '', experience_years: 0, current_ctc: 0, expected_ctc: 0, notice_period_days: 0,
  skills: '', notes: ''
}

const initialInterview = {
  candidate: '', job_opening: '', round_type: 'HR', interviewer: '', scheduled_at: '', duration_minutes: 60,
  mode: 'ONLINE', meeting_link: '', location: ''
}

const initialOffer = {
  offer_number: '', candidate: '', job_opening: '', department: '', offered_designation: '', joining_date: '',
  salary_basic: 0, ctc: 0, valid_until: '', notes: ''
}

export default function Recruitment() {
  const { user } = useAuth()
  const canManage = hasRole(user, HR_ROLES)
  const [jobs, setJobs] = useState([])
  const [candidates, setCandidates] = useState([])
  const [interviews, setInterviews] = useState([])
  const [offers, setOffers] = useState([])
  const [employees, setEmployees] = useState([])
  const [departments, setDepartments] = useState([])
  const [jobForm, setJobForm] = useState(initialJob)
  const [candidateForm, setCandidateForm] = useState(initialCandidate)
  const [interviewForm, setInterviewForm] = useState(initialInterview)
  const [offerForm, setOfferForm] = useState(initialOffer)
  const [resume, setResume] = useState(null)
  const [offerDoc, setOfferDoc] = useState(null)
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
      api.get('/job-openings/'),
      api.get('/candidates/'),
      api.get('/interviews/'),
      api.get('/offers/')
    ]
    if (canManage) {
      requests.push(api.get('/employees/'))
      requests.push(api.get('/departments/'))
    }
    const responses = await Promise.all(requests)
    setJobs(normalize(responses[0].data))
    setCandidates(normalize(responses[1].data))
    setInterviews(normalize(responses[2].data))
    setOffers(normalize(responses[3].data))
    if (canManage) {
      setEmployees(normalize(responses[4].data))
      setDepartments(normalize(responses[5].data))
    }
  }

  useEffect(() => { load().catch(showError) }, [])

  const cleanPayload = (payload) => {
    const output = { ...payload }
    Object.keys(output).forEach(key => {
      if (output[key] === '') output[key] = null
    })
    return output
  }

  const createJob = async (e) => {
    e.preventDefault()
    try {
      await api.post('/job-openings/', cleanPayload(jobForm))
      setJobForm(initialJob)
      await load()
      showMessage('Job opening created.')
    } catch (err) {
      showError(err)
    }
  }

  const jobAction = async (row, action) => {
    try {
      await api.post(`/job-openings/${row.id}/${action}/`)
      await load()
      showMessage('Job opening updated.')
    } catch (err) {
      showError(err)
    }
  }

  const createCandidate = async (e) => {
    e.preventDefault()
    try {
      const formData = new FormData()
      Object.entries(candidateForm).forEach(([key, value]) => formData.append(key, value === '' ? '' : value))
      if (resume) formData.append('resume', resume)
      await api.post('/candidates/', formData)
      setCandidateForm(initialCandidate)
      setResume(null)
      const input = document.getElementById('candidateResume')
      if (input) input.value = ''
      await load()
      showMessage('Candidate added.')
    } catch (err) {
      showError(err)
    }
  }

  const candidateAction = async (row, action) => {
    const payload = {}
    if (action === 'reject') payload.reason = window.prompt('Rejection reason') || ''
    try {
      await api.post(`/candidates/${row.id}/${action}/`, payload)
      await load()
      showMessage('Candidate status updated.')
    } catch (err) {
      showError(err)
    }
  }

  const downloadResume = async (row) => {
    try {
      const res = await api.get(`/candidates/${row.id}/download-resume/`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', row.resume_file_name || `candidate-${row.id}-resume`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      showError(err)
    }
  }

  const scheduleInterview = async (e) => {
    e.preventDefault()
    try {
      await api.post('/interviews/', cleanPayload(interviewForm))
      setInterviewForm(initialInterview)
      await load()
      showMessage('Interview scheduled.')
    } catch (err) {
      showError(err)
    }
  }

  const completeInterview = async (row) => {
    const result = window.prompt('Result: SELECTED, REJECTED, HOLD', 'SELECTED') || 'SELECTED'
    const rating = window.prompt('Rating 0-5', row.rating || '4') || '0'
    const feedback = window.prompt('Feedback') || ''
    try {
      await api.post(`/interviews/${row.id}/complete/`, { result, rating, feedback })
      await load()
      showMessage('Interview completed.')
    } catch (err) {
      showError(err)
    }
  }

  const cancelInterview = async (row) => {
    const reason = window.prompt('Cancellation reason') || ''
    try {
      await api.post(`/interviews/${row.id}/cancel/`, { reason })
      await load()
      showMessage('Interview cancelled.')
    } catch (err) {
      showError(err)
    }
  }

  const createOffer = async (e) => {
    e.preventDefault()
    try {
      const formData = new FormData()
      Object.entries(offerForm).forEach(([key, value]) => formData.append(key, value === '' ? '' : value))
      if (offerDoc) formData.append('document', offerDoc)
      await api.post('/offers/', formData)
      setOfferForm(initialOffer)
      setOfferDoc(null)
      const input = document.getElementById('offerDocument')
      if (input) input.value = ''
      await load()
      showMessage('Offer created.')
    } catch (err) {
      showError(err)
    }
  }

  const offerAction = async (row, action) => {
    try {
      await api.post(`/offers/${row.id}/${action}/`)
      await load()
      showMessage('Offer updated.')
    } catch (err) {
      showError(err)
    }
  }

  const convertOffer = async (row) => {
    const employee_code = window.prompt('Employee code') || ''
    const password = window.prompt('Initial password minimum 8 characters') || ''
    const role = window.prompt('Role', 'EMPLOYEE') || 'EMPLOYEE'
    if (!employee_code || !password) return
    try {
      await api.post(`/offers/${row.id}/convert-to-employee/`, {
        employee_code,
        password,
        role,
        department: row.department,
        designation: row.offered_designation,
        date_of_joining: row.joining_date,
        salary_basic: row.salary_basic
      })
      await load()
      showMessage('Candidate converted to employee.')
    } catch (err) {
      showError(err)
    }
  }

  const downloadOffer = async (row) => {
    try {
      const res = await api.get(`/offers/${row.id}/download-document/`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', row.document_file_name || `offer-${row.id}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      showError(err)
    }
  }

  return (
    <section>
      <PageHeader title="Recruitment / ATS" subtitle="Manage job openings, candidates, resume storage, interviews, offers, and candidate-to-employee conversion." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="infoCard">Workflow: create job opening → publish → add candidate → schedule interview → complete feedback → create offer → accept → convert to employee.</div>

      {canManage && <>
        <h3>1. Create Job Opening</h3>
        <form className="inlineForm wideForm" onSubmit={createJob}>
          <input placeholder="Job code" value={jobForm.job_code} onChange={e => setJobForm({ ...jobForm, job_code: e.target.value })} required />
          <input placeholder="Title" value={jobForm.title} onChange={e => setJobForm({ ...jobForm, title: e.target.value })} required />
          <select value={jobForm.department} onChange={e => setJobForm({ ...jobForm, department: e.target.value })}>
            <option value="">Department</option>
            {departments.map(dep => <option key={dep.id} value={dep.id}>{dep.name}</option>)}
          </select>
          <select value={jobForm.hiring_manager} onChange={e => setJobForm({ ...jobForm, hiring_manager: e.target.value })}>
            <option value="">Hiring manager</option>
            {employees.map(emp => <option key={emp.id} value={emp.id}>{emp.full_name} - {emp.employee_code}</option>)}
          </select>
          <select value={jobForm.employment_type} onChange={e => setJobForm({ ...jobForm, employment_type: e.target.value })}>
            <option value="FULL_TIME">Full Time</option><option value="PART_TIME">Part Time</option><option value="CONTRACT">Contract</option><option value="INTERN">Intern</option>
          </select>
          <select value={jobForm.work_mode} onChange={e => setJobForm({ ...jobForm, work_mode: e.target.value })}>
            <option value="OFFICE">Office</option><option value="REMOTE">Remote</option><option value="HYBRID">Hybrid</option><option value="FIELD">Field</option>
          </select>
          <input placeholder="Location" value={jobForm.location} onChange={e => setJobForm({ ...jobForm, location: e.target.value })} />
          <input type="number" placeholder="Openings" value={jobForm.openings_count} onChange={e => setJobForm({ ...jobForm, openings_count: e.target.value })} />
          <input type="number" placeholder="Min exp" value={jobForm.min_experience} onChange={e => setJobForm({ ...jobForm, min_experience: e.target.value })} />
          <input type="number" placeholder="Max exp" value={jobForm.max_experience} onChange={e => setJobForm({ ...jobForm, max_experience: e.target.value })} />
          <input type="number" placeholder="Salary min" value={jobForm.salary_min} onChange={e => setJobForm({ ...jobForm, salary_min: e.target.value })} />
          <input type="number" placeholder="Salary max" value={jobForm.salary_max} onChange={e => setJobForm({ ...jobForm, salary_max: e.target.value })} />
          <input type="date" value={jobForm.target_start_date} onChange={e => setJobForm({ ...jobForm, target_start_date: e.target.value })} />
          <input placeholder="Description" value={jobForm.description} onChange={e => setJobForm({ ...jobForm, description: e.target.value })} />
          <input placeholder="Requirements" value={jobForm.requirements} onChange={e => setJobForm({ ...jobForm, requirements: e.target.value })} />
          <button>Create Job</button>
        </form>
      </>}

      <h3>2. Job Openings</h3>
      <DataTable columns={[
        { key: 'job_code', label: 'Code' }, { key: 'title', label: 'Title' }, { key: 'department_name', label: 'Department' },
        { key: 'hiring_manager_name', label: 'Hiring Manager' }, { key: 'status', label: 'Status' }, { key: 'openings_count', label: 'Openings' },
        { key: 'candidate_count', label: 'Candidates' },
        { key: 'actions', label: 'Actions', render: row => canManage ? <div className="actions">
          {['DRAFT', 'ON_HOLD'].includes(row.status) && <button onClick={() => jobAction(row, 'publish')}>Publish</button>}
          {['DRAFT', 'OPEN'].includes(row.status) && <button onClick={() => jobAction(row, 'hold')}>Hold</button>}
          {!['CLOSED', 'CANCELLED'].includes(row.status) && <button onClick={() => jobAction(row, 'close')}>Close</button>}
          {!['CLOSED', 'CANCELLED'].includes(row.status) && <button className="dangerBtn" onClick={() => jobAction(row, 'cancel')}>Cancel</button>}
        </div> : '' }
      ]} rows={jobs} />

      {canManage && <>
        <h3>3. Add Candidate</h3>
        <form className="inlineForm wideForm" onSubmit={createCandidate}>
          <select value={candidateForm.job_opening} onChange={e => setCandidateForm({ ...candidateForm, job_opening: e.target.value })}>
            <option value="">Job opening</option>{jobs.map(job => <option key={job.id} value={job.id}>{job.job_code} - {job.title}</option>)}
          </select>
          <input placeholder="First name" value={candidateForm.first_name} onChange={e => setCandidateForm({ ...candidateForm, first_name: e.target.value })} required />
          <input placeholder="Last name" value={candidateForm.last_name} onChange={e => setCandidateForm({ ...candidateForm, last_name: e.target.value })} />
          <input type="email" placeholder="Email" value={candidateForm.email} onChange={e => setCandidateForm({ ...candidateForm, email: e.target.value })} required />
          <input placeholder="Phone" value={candidateForm.phone} onChange={e => setCandidateForm({ ...candidateForm, phone: e.target.value })} />
          <select value={candidateForm.source} onChange={e => setCandidateForm({ ...candidateForm, source: e.target.value })}>
            <option value="JOB_PORTAL">Job Portal</option><option value="LINKEDIN">LinkedIn</option><option value="REFERRAL">Referral</option><option value="AGENCY">Agency</option><option value="OTHER">Other</option>
          </select>
          <input placeholder="Current company" value={candidateForm.current_company} onChange={e => setCandidateForm({ ...candidateForm, current_company: e.target.value })} />
          <input placeholder="Designation" value={candidateForm.current_designation} onChange={e => setCandidateForm({ ...candidateForm, current_designation: e.target.value })} />
          <input type="number" placeholder="Experience" value={candidateForm.experience_years} onChange={e => setCandidateForm({ ...candidateForm, experience_years: e.target.value })} />
          <input type="number" placeholder="Expected CTC" value={candidateForm.expected_ctc} onChange={e => setCandidateForm({ ...candidateForm, expected_ctc: e.target.value })} />
          <input type="number" placeholder="Notice days" value={candidateForm.notice_period_days} onChange={e => setCandidateForm({ ...candidateForm, notice_period_days: e.target.value })} />
          <input placeholder="Skills" value={candidateForm.skills} onChange={e => setCandidateForm({ ...candidateForm, skills: e.target.value })} />
          <input id="candidateResume" type="file" onChange={e => setResume(e.target.files[0])} />
          <button>Add Candidate</button>
        </form>
      </>}

      <h3>4. Candidates</h3>
      <DataTable columns={[
        { key: 'full_name', label: 'Candidate' }, { key: 'email', label: 'Email' }, { key: 'job_title', label: 'Job' },
        { key: 'source', label: 'Source' }, { key: 'experience_years', label: 'Exp' }, { key: 'expected_ctc', label: 'Expected CTC' }, { key: 'status', label: 'Status' },
        { key: 'actions', label: 'Actions', render: row => <div className="actions">
          {row.resume_file_name && <button onClick={() => downloadResume(row)}>Resume</button>}
          {canManage && <button onClick={() => candidateAction(row, 'screen')}>Screen</button>}
          {canManage && <button onClick={() => candidateAction(row, 'shortlist')}>Shortlist</button>}
          {canManage && <button onClick={() => candidateAction(row, 'hold')}>Hold</button>}
          {canManage && <button className="dangerBtn" onClick={() => candidateAction(row, 'reject')}>Reject</button>}
        </div> }
      ]} rows={candidates} />

      {canManage && <>
        <h3>5. Schedule Interview</h3>
        <form className="inlineForm wideForm" onSubmit={scheduleInterview}>
          <select value={interviewForm.candidate} onChange={e => setInterviewForm({ ...interviewForm, candidate: e.target.value })} required>
            <option value="">Candidate</option>{candidates.map(c => <option key={c.id} value={c.id}>{c.full_name} - {c.email}</option>)}
          </select>
          <select value={interviewForm.job_opening} onChange={e => setInterviewForm({ ...interviewForm, job_opening: e.target.value })}>
            <option value="">Job</option>{jobs.map(job => <option key={job.id} value={job.id}>{job.job_code} - {job.title}</option>)}
          </select>
          <select value={interviewForm.round_type} onChange={e => setInterviewForm({ ...interviewForm, round_type: e.target.value })}>
            <option value="HR">HR</option><option value="TECHNICAL">Technical</option><option value="MANAGERIAL">Managerial</option><option value="FINAL">Final</option>
          </select>
          <select value={interviewForm.interviewer} onChange={e => setInterviewForm({ ...interviewForm, interviewer: e.target.value })}>
            <option value="">Interviewer</option>{employees.map(emp => <option key={emp.id} value={emp.id}>{emp.full_name} - {emp.employee_code}</option>)}
          </select>
          <input type="datetime-local" value={interviewForm.scheduled_at} onChange={e => setInterviewForm({ ...interviewForm, scheduled_at: e.target.value })} />
          <input type="number" placeholder="Duration" value={interviewForm.duration_minutes} onChange={e => setInterviewForm({ ...interviewForm, duration_minutes: e.target.value })} />
          <select value={interviewForm.mode} onChange={e => setInterviewForm({ ...interviewForm, mode: e.target.value })}>
            <option value="ONLINE">Online</option><option value="OFFLINE">Offline</option><option value="PHONE">Phone</option>
          </select>
          <input placeholder="Meeting link" value={interviewForm.meeting_link} onChange={e => setInterviewForm({ ...interviewForm, meeting_link: e.target.value })} />
          <input placeholder="Location" value={interviewForm.location} onChange={e => setInterviewForm({ ...interviewForm, location: e.target.value })} />
          <button>Schedule</button>
        </form>
      </>}

      <h3>6. Interviews</h3>
      <DataTable columns={[
        { key: 'candidate_name', label: 'Candidate' }, { key: 'job_title', label: 'Job' }, { key: 'round_type', label: 'Round' },
        { key: 'interviewer_name', label: 'Interviewer' }, { key: 'scheduled_at', label: 'Schedule' }, { key: 'status', label: 'Status' }, { key: 'result', label: 'Result' }, { key: 'rating', label: 'Rating' },
        { key: 'actions', label: 'Actions', render: row => <div className="actions">
          {row.status === 'SCHEDULED' && <button onClick={() => completeInterview(row)}>Complete</button>}
          {row.status === 'SCHEDULED' && <button className="dangerBtn" onClick={() => cancelInterview(row)}>Cancel</button>}
        </div> }
      ]} rows={interviews} />

      {canManage && <>
        <h3>7. Create Offer</h3>
        <form className="inlineForm wideForm" onSubmit={createOffer}>
          <input placeholder="Offer number" value={offerForm.offer_number} onChange={e => setOfferForm({ ...offerForm, offer_number: e.target.value })} required />
          <select value={offerForm.candidate} onChange={e => setOfferForm({ ...offerForm, candidate: e.target.value })} required>
            <option value="">Candidate</option>{candidates.map(c => <option key={c.id} value={c.id}>{c.full_name} - {c.email}</option>)}
          </select>
          <select value={offerForm.job_opening} onChange={e => setOfferForm({ ...offerForm, job_opening: e.target.value })}>
            <option value="">Job</option>{jobs.map(job => <option key={job.id} value={job.id}>{job.job_code} - {job.title}</option>)}
          </select>
          <select value={offerForm.department} onChange={e => setOfferForm({ ...offerForm, department: e.target.value })}>
            <option value="">Department</option>{departments.map(dep => <option key={dep.id} value={dep.id}>{dep.name}</option>)}
          </select>
          <input placeholder="Designation" value={offerForm.offered_designation} onChange={e => setOfferForm({ ...offerForm, offered_designation: e.target.value })} required />
          <input type="date" value={offerForm.joining_date} onChange={e => setOfferForm({ ...offerForm, joining_date: e.target.value })} />
          <input type="number" placeholder="Basic salary" value={offerForm.salary_basic} onChange={e => setOfferForm({ ...offerForm, salary_basic: e.target.value })} />
          <input type="number" placeholder="CTC" value={offerForm.ctc} onChange={e => setOfferForm({ ...offerForm, ctc: e.target.value })} />
          <input type="date" value={offerForm.valid_until} onChange={e => setOfferForm({ ...offerForm, valid_until: e.target.value })} />
          <input placeholder="Notes" value={offerForm.notes} onChange={e => setOfferForm({ ...offerForm, notes: e.target.value })} />
          <input id="offerDocument" type="file" onChange={e => setOfferDoc(e.target.files[0])} />
          <button>Create Offer</button>
        </form>
      </>}

      <h3>8. Offers</h3>
      <DataTable columns={[
        { key: 'offer_number', label: 'Offer' }, { key: 'candidate_name', label: 'Candidate' }, { key: 'job_title', label: 'Job' },
        { key: 'offered_designation', label: 'Designation' }, { key: 'joining_date', label: 'Joining' }, { key: 'ctc', label: 'CTC' }, { key: 'status', label: 'Status' },
        { key: 'actions', label: 'Actions', render: row => <div className="actions">
          {row.document_file_name && <button onClick={() => downloadOffer(row)}>Document</button>}
          {canManage && ['DRAFT', 'SENT'].includes(row.status) && <button onClick={() => offerAction(row, 'send')}>Send</button>}
          {canManage && ['DRAFT', 'SENT'].includes(row.status) && <button onClick={() => offerAction(row, 'accept')}>Accept</button>}
          {canManage && !['CONVERTED', 'WITHDRAWN'].includes(row.status) && <button onClick={() => offerAction(row, 'reject')}>Reject</button>}
          {canManage && row.status !== 'CONVERTED' && <button className="dangerBtn" onClick={() => offerAction(row, 'withdraw')}>Withdraw</button>}
          {canManage && row.status === 'ACCEPTED' && <button onClick={() => convertOffer(row)}>Convert</button>}
        </div> }
      ]} rows={offers} />
    </section>
  )
}
