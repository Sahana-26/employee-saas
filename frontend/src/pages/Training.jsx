import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { HR_ROLES, hasRole } from '../utils/roles.js'

const roleOptions = ['OWNER', 'ADMIN', 'HR', 'MANAGER', 'EMPLOYEE', 'PAYROLL', 'IT', 'VIEWER']

const initialCourse = {
  code: '', title: '', category: '', level: 'BEGINNER', description: '', skills_covered: '',
  duration_hours: 0, is_mandatory: false, audience_roles: []
}

const initialMaterial = {
  course: '', title: '', material_type: 'DOCUMENT', external_url: '', notes: ''
}

const initialEnrollment = {
  course: '', employee: '', due_date: '', progress_percent: 0, notes: ''
}

const initialAssessment = {
  course: '', title: '', instructions: '', max_score: 100, passing_score: 60, questions: '[]', is_published: false
}

export default function Training() {
  const { user } = useAuth()
  const canManage = hasRole(user, HR_ROLES)
  const [courses, setCourses] = useState([])
  const [materials, setMaterials] = useState([])
  const [enrollments, setEnrollments] = useState([])
  const [assessments, setAssessments] = useState([])
  const [submissions, setSubmissions] = useState([])
  const [certificates, setCertificates] = useState([])
  const [employees, setEmployees] = useState([])
  const [courseForm, setCourseForm] = useState(initialCourse)
  const [materialForm, setMaterialForm] = useState(initialMaterial)
  const [enrollmentForm, setEnrollmentForm] = useState(initialEnrollment)
  const [assessmentForm, setAssessmentForm] = useState(initialAssessment)
  const [materialFile, setMaterialFile] = useState(null)
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
      api.get('/training-courses/'),
      api.get('/training-materials/'),
      api.get('/training-enrollments/'),
      api.get('/training-assessments/'),
      api.get('/training-submissions/'),
      api.get('/training-certificates/')
    ]
    if (canManage) requests.push(api.get('/employees/'))
    const responses = await Promise.all(requests)
    setCourses(normalize(responses[0].data))
    setMaterials(normalize(responses[1].data))
    setEnrollments(normalize(responses[2].data))
    setAssessments(normalize(responses[3].data))
    setSubmissions(normalize(responses[4].data))
    setCertificates(normalize(responses[5].data))
    if (canManage) setEmployees(normalize(responses[6].data))
  }

  useEffect(() => { load().catch(showError) }, [canManage])

  const cleanPayload = (payload) => {
    const output = { ...payload }
    Object.keys(output).forEach(key => {
      if (output[key] === '') output[key] = null
    })
    return output
  }

  const toggleRole = (role) => {
    setCourseForm(current => {
      const roles = current.audience_roles.includes(role)
        ? current.audience_roles.filter(item => item !== role)
        : [...current.audience_roles, role]
      return { ...current, audience_roles: roles }
    })
  }

  const createCourse = async (e) => {
    e.preventDefault()
    try {
      await api.post('/training-courses/', courseForm)
      setCourseForm(initialCourse)
      await load()
      showMessage('Training course created.')
    } catch (err) {
      showError(err)
    }
  }

  const courseAction = async (row, action, successText) => {
    try {
      const res = await api.post(`/training-courses/${row.id}/${action}/`)
      await load()
      showMessage(res.data.detail || successText)
    } catch (err) {
      showError(err)
    }
  }

  const selfEnroll = async (row) => courseAction(row, 'self-enroll', 'Course enrolled.')

  const createMaterial = async (e) => {
    e.preventDefault()
    try {
      const formData = new FormData()
      Object.entries(materialForm).forEach(([key, value]) => formData.append(key, value === '' ? '' : value))
      if (materialFile) formData.append('file', materialFile)
      await api.post('/training-materials/', formData)
      setMaterialForm(initialMaterial)
      setMaterialFile(null)
      const input = document.getElementById('trainingMaterialFile')
      if (input) input.value = ''
      await load()
      showMessage('Training material added.')
    } catch (err) {
      showError(err)
    }
  }

  const downloadMaterial = async (row) => {
    try {
      const res = await api.get(`/training-materials/${row.id}/download/`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', row.file_name || `training-material-${row.id}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      showError(err)
    }
  }

  const createEnrollment = async (e) => {
    e.preventDefault()
    try {
      await api.post('/training-enrollments/', cleanPayload(enrollmentForm))
      setEnrollmentForm(initialEnrollment)
      await load()
      showMessage('Employee enrolled in course.')
    } catch (err) {
      showError(err)
    }
  }

  const enrollmentAction = async (row, action, payload = {}) => {
    try {
      await api.post(`/training-enrollments/${row.id}/${action}/`, payload)
      await load()
      showMessage('Training enrollment updated.')
    } catch (err) {
      showError(err)
    }
  }

  const updateProgress = async (row) => {
    const progress = window.prompt('Progress percentage 0-100', row.progress_percent || 0)
    if (progress === null) return
    await enrollmentAction(row, 'update-progress', { progress_percent: progress })
  }

  const createAssessment = async (e) => {
    e.preventDefault()
    try {
      let questions = []
      try {
        questions = JSON.parse(assessmentForm.questions || '[]')
      } catch {
        showError({ response: { data: { detail: 'Questions must be valid JSON.' } } })
        return
      }
      await api.post('/training-assessments/', { ...assessmentForm, questions })
      setAssessmentForm(initialAssessment)
      await load()
      showMessage('Assessment created.')
    } catch (err) {
      showError(err)
    }
  }

  const assessmentAction = async (row, action) => {
    try {
      await api.post(`/training-assessments/${row.id}/${action}/`)
      await load()
      showMessage('Assessment updated.')
    } catch (err) {
      showError(err)
    }
  }

  const submitAssessment = async (row) => {
    const raw = window.prompt('Enter answers as JSON', '{}')
    if (raw === null) return
    try {
      const answers = JSON.parse(raw || '{}')
      await api.post('/training-submissions/', { assessment: row.id, answers })
      await load()
      showMessage('Assessment submitted for review.')
    } catch (err) {
      if (err instanceof SyntaxError) showError({ response: { data: { detail: 'Answers must be valid JSON.' } } })
      else showError(err)
    }
  }

  const reviewSubmission = async (row) => {
    const score = window.prompt('Score', row.score || '0')
    if (score === null) return
    const feedback = window.prompt('Feedback') || ''
    try {
      await api.post(`/training-submissions/${row.id}/review/`, { score, feedback })
      await load()
      showMessage('Submission reviewed.')
    } catch (err) {
      showError(err)
    }
  }

  const downloadCertificate = async (row) => {
    try {
      const res = await api.get(`/training-certificates/${row.id}/download/`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${row.certificate_number || `certificate-${row.id}`}.txt`)
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
      <PageHeader title="Training / LMS" subtitle="Manage courses, materials, enrollments, assessments, progress, and certificates." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="statsGrid smallStats">
        <div className="stat"><span>Courses</span><strong>{courses.length}</strong></div>
        <div className="stat"><span>Enrollments</span><strong>{enrollments.length}</strong></div>
        <div className="stat"><span>Assessments</span><strong>{assessments.length}</strong></div>
        <div className="stat"><span>Certificates</span><strong>{certificates.length}</strong></div>
      </div>

      {canManage && (
        <>
          <h3>Create Course</h3>
          <form className="inlineForm wideForm announcementForm" onSubmit={createCourse}>
            <input placeholder="Course code" value={courseForm.code} onChange={e => setCourseForm({ ...courseForm, code: e.target.value.toUpperCase() })} required />
            <input placeholder="Course title" value={courseForm.title} onChange={e => setCourseForm({ ...courseForm, title: e.target.value })} required />
            <input placeholder="Category" value={courseForm.category} onChange={e => setCourseForm({ ...courseForm, category: e.target.value })} />
            <select value={courseForm.level} onChange={e => setCourseForm({ ...courseForm, level: e.target.value })}>
              <option value="BEGINNER">BEGINNER</option>
              <option value="INTERMEDIATE">INTERMEDIATE</option>
              <option value="ADVANCED">ADVANCED</option>
              <option value="COMPLIANCE">COMPLIANCE</option>
            </select>
            <input type="number" placeholder="Duration hours" value={courseForm.duration_hours} onChange={e => setCourseForm({ ...courseForm, duration_hours: e.target.value })} />
            <textarea placeholder="Description" value={courseForm.description} onChange={e => setCourseForm({ ...courseForm, description: e.target.value })} />
            <textarea placeholder="Skills covered" value={courseForm.skills_covered} onChange={e => setCourseForm({ ...courseForm, skills_covered: e.target.value })} />
            <label className="checkLabel"><input type="checkbox" checked={courseForm.is_mandatory} onChange={e => setCourseForm({ ...courseForm, is_mandatory: e.target.checked })} /> Mandatory</label>
            <div className="rolePicker">
              <strong>Audience roles</strong>
              <small>Leave all unchecked to show to everyone.</small>
              <div>{roleOptions.map(role => <label key={role} className="checkLabel"><input type="checkbox" checked={courseForm.audience_roles.includes(role)} onChange={() => toggleRole(role)} /> {role}</label>)}</div>
            </div>
            <button>Create Course</button>
          </form>

          <h3>Add Material</h3>
          <form className="inlineForm wideForm" onSubmit={createMaterial}>
            <select value={materialForm.course} onChange={e => setMaterialForm({ ...materialForm, course: e.target.value })} required>
              <option value="">Course</option>
              {courses.map(course => <option key={course.id} value={course.id}>{course.code} - {course.title}</option>)}
            </select>
            <input placeholder="Material title" value={materialForm.title} onChange={e => setMaterialForm({ ...materialForm, title: e.target.value })} required />
            <select value={materialForm.material_type} onChange={e => setMaterialForm({ ...materialForm, material_type: e.target.value })}>
              <option value="DOCUMENT">DOCUMENT</option>
              <option value="VIDEO">VIDEO</option>
              <option value="LINK">LINK</option>
              <option value="SLIDE">SLIDE</option>
              <option value="OTHER">OTHER</option>
            </select>
            <input placeholder="External URL" value={materialForm.external_url} onChange={e => setMaterialForm({ ...materialForm, external_url: e.target.value })} />
            <input id="trainingMaterialFile" type="file" onChange={e => setMaterialFile(e.target.files?.[0] || null)} />
            <input placeholder="Notes" value={materialForm.notes} onChange={e => setMaterialForm({ ...materialForm, notes: e.target.value })} />
            <button>Add Material</button>
          </form>

          <h3>Assign Course</h3>
          <form className="inlineForm wideForm" onSubmit={createEnrollment}>
            <select value={enrollmentForm.course} onChange={e => setEnrollmentForm({ ...enrollmentForm, course: e.target.value })} required>
              <option value="">Course</option>
              {courses.map(course => <option key={course.id} value={course.id}>{course.code} - {course.title}</option>)}
            </select>
            <select value={enrollmentForm.employee} onChange={e => setEnrollmentForm({ ...enrollmentForm, employee: e.target.value })} required>
              <option value="">Employee</option>
              {employees.map(emp => <option key={emp.id} value={emp.id}>{emp.employee_code} - {emp.user_email || emp.email || emp.employee_name}</option>)}
            </select>
            <input type="date" value={enrollmentForm.due_date || ''} onChange={e => setEnrollmentForm({ ...enrollmentForm, due_date: e.target.value })} />
            <input placeholder="Notes" value={enrollmentForm.notes} onChange={e => setEnrollmentForm({ ...enrollmentForm, notes: e.target.value })} />
            <button>Assign</button>
          </form>

          <h3>Create Assessment</h3>
          <form className="inlineForm wideForm announcementForm" onSubmit={createAssessment}>
            <select value={assessmentForm.course} onChange={e => setAssessmentForm({ ...assessmentForm, course: e.target.value })} required>
              <option value="">Course</option>
              {courses.map(course => <option key={course.id} value={course.id}>{course.code} - {course.title}</option>)}
            </select>
            <input placeholder="Assessment title" value={assessmentForm.title} onChange={e => setAssessmentForm({ ...assessmentForm, title: e.target.value })} required />
            <input type="number" placeholder="Max score" value={assessmentForm.max_score} onChange={e => setAssessmentForm({ ...assessmentForm, max_score: e.target.value })} />
            <input type="number" placeholder="Passing score" value={assessmentForm.passing_score} onChange={e => setAssessmentForm({ ...assessmentForm, passing_score: e.target.value })} />
            <textarea placeholder="Instructions" value={assessmentForm.instructions} onChange={e => setAssessmentForm({ ...assessmentForm, instructions: e.target.value })} />
            <textarea placeholder='Questions JSON, e.g. [{"q":"What is HR policy?","marks":10}]' value={assessmentForm.questions} onChange={e => setAssessmentForm({ ...assessmentForm, questions: e.target.value })} />
            <label className="checkLabel"><input type="checkbox" checked={assessmentForm.is_published} onChange={e => setAssessmentForm({ ...assessmentForm, is_published: e.target.checked })} /> Publish immediately</label>
            <button>Create Assessment</button>
          </form>
        </>
      )}

      <h3>Courses</h3>
      <DataTable columns={[
        { key: 'code', label: 'Code' },
        { key: 'title', label: 'Title' },
        { key: 'category', label: 'Category' },
        { key: 'level', label: 'Level' },
        { key: 'duration_hours', label: 'Hours' },
        { key: 'status', label: 'Status' },
        { key: 'material_count', label: 'Materials' },
        { key: 'enrollment_count', label: 'Enrollments' },
        { key: 'my_progress_percent', label: 'My Progress', render: row => row.my_progress_percent === null || row.my_progress_percent === undefined ? '-' : `${row.my_progress_percent}%` },
        { key: 'actions', label: 'Actions', render: row => (
          <div className="actions">
            {canManage && row.status !== 'PUBLISHED' && <button onClick={() => courseAction(row, 'publish', 'Course published.')}>Publish</button>}
            {canManage && row.status === 'PUBLISHED' && <button className="dangerBtn" onClick={() => courseAction(row, 'archive', 'Course archived.')}>Archive</button>}
            {!canManage && row.status === 'PUBLISHED' && !row.is_enrolled_by_me && <button onClick={() => selfEnroll(row)}>Enroll</button>}
          </div>
        ) }
      ]} rows={courses} />

      <h3>Materials</h3>
      <DataTable columns={[
        { key: 'course_title', label: 'Course' },
        { key: 'title', label: 'Title' },
        { key: 'material_type', label: 'Type' },
        { key: 'file_name', label: 'File' },
        { key: 'external_url', label: 'URL', render: row => row.external_url ? <a href={row.external_url} target="_blank" rel="noreferrer">Open</a> : '-' },
        { key: 'actions', label: 'Actions', render: row => <div className="actions">{row.has_file && <button onClick={() => downloadMaterial(row)}>Download</button>}</div> }
      ]} rows={materials} />

      <h3>Enrollments</h3>
      <DataTable columns={[
        { key: 'course_title', label: 'Course' },
        { key: 'employee_code', label: 'Employee Code' },
        { key: 'employee_name', label: 'Employee' },
        { key: 'status', label: 'Status' },
        { key: 'progress_percent', label: 'Progress', render: row => `${row.progress_percent}%` },
        { key: 'due_date', label: 'Due Date' },
        { key: 'certificate_number', label: 'Certificate' },
        { key: 'actions', label: 'Actions', render: row => (
          <div className="actions">
            {row.status === 'ASSIGNED' && <button onClick={() => enrollmentAction(row, 'start')}>Start</button>}
            {row.status !== 'COMPLETED' && row.status !== 'CANCELLED' && <button onClick={() => updateProgress(row)}>Progress</button>}
            {row.status !== 'COMPLETED' && row.status !== 'CANCELLED' && <button onClick={() => enrollmentAction(row, 'complete')}>Complete</button>}
            {canManage && row.status === 'COMPLETED' && !row.certificate_number && <button onClick={() => enrollmentAction(row, 'issue-certificate')}>Certificate</button>}
            {canManage && row.status !== 'CANCELLED' && <button className="dangerBtn" onClick={() => enrollmentAction(row, 'cancel')}>Cancel</button>}
          </div>
        ) }
      ]} rows={enrollments} />

      <h3>Assessments</h3>
      <DataTable columns={[
        { key: 'course_title', label: 'Course' },
        { key: 'title', label: 'Title' },
        { key: 'max_score', label: 'Max' },
        { key: 'passing_score', label: 'Pass' },
        { key: 'is_published', label: 'Published', render: row => row.is_published ? 'Yes' : 'No' },
        { key: 'submission_count', label: 'Submissions' },
        { key: 'actions', label: 'Actions', render: row => (
          <div className="actions">
            {canManage && !row.is_published && <button onClick={() => assessmentAction(row, 'publish')}>Publish</button>}
            {canManage && row.is_published && <button className="dangerBtn" onClick={() => assessmentAction(row, 'archive')}>Archive</button>}
            {!canManage && row.is_published && <button onClick={() => submitAssessment(row)}>Submit</button>}
          </div>
        ) }
      ]} rows={assessments} />

      <h3>Submissions</h3>
      <DataTable columns={[
        { key: 'course_title', label: 'Course' },
        { key: 'assessment_title', label: 'Assessment' },
        { key: 'employee_code', label: 'Employee Code' },
        { key: 'employee_name', label: 'Employee' },
        { key: 'score', label: 'Score' },
        { key: 'status', label: 'Status' },
        { key: 'feedback', label: 'Feedback' },
        { key: 'actions', label: 'Actions', render: row => <div className="actions">{canManage && <button onClick={() => reviewSubmission(row)}>Review</button>}</div> }
      ]} rows={submissions} />

      <h3>Certificates</h3>
      <DataTable columns={[
        { key: 'certificate_number', label: 'Certificate No.' },
        { key: 'course_title', label: 'Course' },
        { key: 'employee_code', label: 'Employee Code' },
        { key: 'employee_name', label: 'Employee' },
        { key: 'issued_at', label: 'Issued At' },
        { key: 'actions', label: 'Actions', render: row => <div className="actions"><button onClick={() => downloadCertificate(row)}>Download</button></div> }
      ]} rows={certificates} />
    </section>
  )
}
