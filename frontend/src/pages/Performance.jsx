import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { HR_ROLES, MANAGER_ROLES, hasRole } from '../utils/roles.js'

const cyclePeriods = ['ANNUAL', 'HALF_YEARLY', 'QUARTERLY', 'PROBATION', 'PROJECT']
const goalCategories = ['KRA', 'SKILL', 'BEHAVIOR', 'PROJECT', 'LEADERSHIP']

export default function Performance() {
  const { user } = useAuth()
  const canManageHR = hasRole(user, HR_ROLES)
  const canReviewTeam = hasRole(user, MANAGER_ROLES)
  const normalize = data => data.results || data

  const [cycles, setCycles] = useState([])
  const [employees, setEmployees] = useState([])
  const [goals, setGoals] = useState([])
  const [reviews, setReviews] = useState([])
  const [selectedCycle, setSelectedCycle] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const [cycleForm, setCycleForm] = useState({
    name: '',
    year: new Date().getFullYear(),
    period: 'ANNUAL',
    start_date: '',
    end_date: '',
    self_review_start: '',
    self_review_end: '',
    manager_review_start: '',
    manager_review_end: '',
    hr_calibration_start: '',
    hr_calibration_end: '',
    description: ''
  })

  const [goalForm, setGoalForm] = useState({
    cycle: '',
    employee: '',
    title: '',
    description: '',
    category: 'KRA',
    weightage: '0',
    target_value: '',
    measurement_unit: '',
    due_date: ''
  })

  const [reviewForm, setReviewForm] = useState({ cycle: '', employee: '', manager: '' })
  const [selfReviewForm, setSelfReviewForm] = useState({ reviewId: '', self_summary: '', strengths: '', improvement_areas: '', career_goals: '' })
  const [managerReviewForm, setManagerReviewForm] = useState({ reviewId: '', manager_summary: '', manager_rating: '3' })
  const [finalizeForm, setFinalizeForm] = useState({ reviewId: '', hr_comments: '', final_rating: '3', final_score: '60' })
  const [goalReviewForm, setGoalReviewForm] = useState({ goalId: '', self_rating: '3', self_comment: '', manager_rating: '3', manager_comment: '' })

  const showError = (err) => {
    setMessage('')
    setError(err?.response?.data?.detail || JSON.stringify(err?.response?.data || {}) || 'Something went wrong')
  }

  const showMessage = (text) => {
    setError('')
    setMessage(text)
  }

  const load = async () => {
    const [cycleRes, employeeRes, goalRes, reviewRes] = await Promise.all([
      api.get('/performance-cycles/'),
      api.get('/employees/'),
      api.get(selectedCycle ? `/performance-goals/?cycle=${selectedCycle}` : '/performance-goals/'),
      api.get(selectedCycle ? `/performance-reviews/?cycle=${selectedCycle}` : '/performance-reviews/')
    ])
    const cycleData = normalize(cycleRes.data)
    setCycles(cycleData)
    setEmployees(normalize(employeeRes.data))
    setGoals(normalize(goalRes.data))
    setReviews(normalize(reviewRes.data))
    if (!selectedCycle && cycleData.length) {
      const active = cycleData.find(item => item.status === 'ACTIVE') || cycleData[0]
      setSelectedCycle(String(active.id))
      setGoalForm(current => ({ ...current, cycle: String(active.id) }))
      setReviewForm(current => ({ ...current, cycle: String(active.id) }))
    }
  }

  useEffect(() => { load().catch(showError) }, [selectedCycle])

  const employeeOptions = useMemo(() => employees.map(emp => ({
    id: emp.id,
    label: `${emp.employee_code} - ${emp.full_name || emp.user_email}`
  })), [employees])

  const createCycle = async (e) => {
    e.preventDefault()
    try {
      const payload = { ...cycleForm }
      Object.keys(payload).forEach(key => { if (payload[key] === '') payload[key] = null })
      await api.post('/performance-cycles/', payload)
      setCycleForm({ name: '', year: new Date().getFullYear(), period: 'ANNUAL', start_date: '', end_date: '', self_review_start: '', self_review_end: '', manager_review_start: '', manager_review_end: '', hr_calibration_start: '', hr_calibration_end: '', description: '' })
      await load()
      showMessage('Performance cycle created.')
    } catch (err) {
      showError(err)
    }
  }

  const createGoal = async (e) => {
    e.preventDefault()
    try {
      const payload = { ...goalForm, cycle: goalForm.cycle || selectedCycle }
      Object.keys(payload).forEach(key => { if (payload[key] === '') payload[key] = null })
      await api.post('/performance-goals/', payload)
      setGoalForm(current => ({ ...current, title: '', description: '', weightage: '0', target_value: '', measurement_unit: '', due_date: '' }))
      await load()
      showMessage('Performance goal created.')
    } catch (err) {
      showError(err)
    }
  }

  const createReview = async (e) => {
    e.preventDefault()
    try {
      const payload = { ...reviewForm, cycle: reviewForm.cycle || selectedCycle }
      if (!payload.manager) delete payload.manager
      await api.post('/performance-reviews/', payload)
      setReviewForm(current => ({ ...current, employee: '', manager: '' }))
      await load()
      showMessage('Review record created.')
    } catch (err) {
      showError(err)
    }
  }

  const action = async (url, successText, payload = {}) => {
    try {
      const res = await api.post(url, payload)
      await load()
      showMessage(res.data.detail || successText)
    } catch (err) {
      showError(err)
    }
  }

  const rejectGoal = async (goal) => {
    const reason = window.prompt('Reason for rejecting this goal?')
    if (!reason) return
    await action(`/performance-goals/${goal.id}/reject/`, 'Goal rejected.', { reason })
  }

  const submitSelfReview = async (e) => {
    e.preventDefault()
    await action(`/performance-reviews/${selfReviewForm.reviewId}/submit-self-review/`, 'Self-review submitted.', {
      self_summary: selfReviewForm.self_summary,
      strengths: selfReviewForm.strengths,
      improvement_areas: selfReviewForm.improvement_areas,
      career_goals: selfReviewForm.career_goals
    })
  }

  const submitManagerReview = async (e) => {
    e.preventDefault()
    await action(`/performance-reviews/${managerReviewForm.reviewId}/submit-manager-review/`, 'Manager review submitted.', {
      manager_summary: managerReviewForm.manager_summary,
      manager_rating: managerReviewForm.manager_rating
    })
  }

  const finalizeReview = async (e) => {
    e.preventDefault()
    await action(`/performance-reviews/${finalizeForm.reviewId}/finalize/`, 'Review finalized.', {
      hr_comments: finalizeForm.hr_comments,
      final_rating: finalizeForm.final_rating,
      final_score: finalizeForm.final_score
    })
  }

  const saveGoalSelfReview = async (e) => {
    e.preventDefault()
    await action(`/performance-goals/${goalReviewForm.goalId}/self-review/`, 'Goal self-review saved.', {
      self_rating: goalReviewForm.self_rating,
      self_comment: goalReviewForm.self_comment
    })
  }

  const saveGoalManagerReview = async (e) => {
    e.preventDefault()
    await action(`/performance-goals/${goalReviewForm.goalId}/manager-review/`, 'Goal manager review saved.', {
      manager_rating: goalReviewForm.manager_rating,
      manager_comment: goalReviewForm.manager_comment
    })
  }

  return (
    <section>
      <PageHeader title="Performance Reviews" subtitle="Manage appraisal cycles, KRAs, self-review, manager review, HR calibration, and final ratings." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <form className="inlineForm wideForm" onSubmit={(e) => { e.preventDefault(); load().catch(showError) }}>
        <select value={selectedCycle} onChange={e => setSelectedCycle(e.target.value)}>
          <option value="">All cycles</option>
          {cycles.map(cycle => <option key={cycle.id} value={cycle.id}>{cycle.name} {cycle.year} - {cycle.status}</option>)}
        </select>
        <button>Refresh</button>
      </form>

      {canManageHR && (
        <>
          <h3>Create Review Cycle</h3>
          <form className="inlineForm wideForm announcementForm" onSubmit={createCycle}>
            <input placeholder="Cycle name" value={cycleForm.name} onChange={e => setCycleForm({ ...cycleForm, name: e.target.value })} required />
            <input type="number" placeholder="Year" value={cycleForm.year} onChange={e => setCycleForm({ ...cycleForm, year: e.target.value })} required />
            <select value={cycleForm.period} onChange={e => setCycleForm({ ...cycleForm, period: e.target.value })}>{cyclePeriods.map(period => <option key={period} value={period}>{period}</option>)}</select>
            <input type="date" value={cycleForm.start_date} onChange={e => setCycleForm({ ...cycleForm, start_date: e.target.value })} required />
            <input type="date" value={cycleForm.end_date} onChange={e => setCycleForm({ ...cycleForm, end_date: e.target.value })} required />
            <input type="date" title="Self review start" value={cycleForm.self_review_start} onChange={e => setCycleForm({ ...cycleForm, self_review_start: e.target.value })} />
            <input type="date" title="Self review end" value={cycleForm.self_review_end} onChange={e => setCycleForm({ ...cycleForm, self_review_end: e.target.value })} />
            <input type="date" title="Manager review start" value={cycleForm.manager_review_start} onChange={e => setCycleForm({ ...cycleForm, manager_review_start: e.target.value })} />
            <input type="date" title="Manager review end" value={cycleForm.manager_review_end} onChange={e => setCycleForm({ ...cycleForm, manager_review_end: e.target.value })} />
            <textarea placeholder="Description" value={cycleForm.description} onChange={e => setCycleForm({ ...cycleForm, description: e.target.value })} />
            <button>Create Cycle</button>
          </form>
        </>
      )}

      <h3>Review Cycles</h3>
      <DataTable columns={[
        { key: 'name', label: 'Name' },
        { key: 'year', label: 'Year' },
        { key: 'period', label: 'Period' },
        { key: 'status', label: 'Status' },
        { key: 'start_date', label: 'Start' },
        { key: 'end_date', label: 'End' },
        { key: 'goal_count', label: 'Goals' },
        { key: 'review_count', label: 'Reviews' },
        { key: 'finalized_count', label: 'Finalized' },
        { key: 'actions', label: 'Actions', render: row => (
          <div className="actions">
            {canManageHR && row.status !== 'ACTIVE' && <button onClick={() => action(`/performance-cycles/${row.id}/publish/`, 'Cycle published.')}>Publish</button>}
            {canManageHR && row.status !== 'CLOSED' && <button className="dangerBtn" onClick={() => action(`/performance-cycles/${row.id}/close/`, 'Cycle closed.')}>Close</button>}
          </div>
        )}
      ]} rows={cycles} />

      <h3>Create Goal / KRA</h3>
      <form className="inlineForm wideForm announcementForm" onSubmit={createGoal}>
        <select value={goalForm.cycle || selectedCycle} onChange={e => setGoalForm({ ...goalForm, cycle: e.target.value })} required>
          <option value="">Select cycle</option>
          {cycles.map(cycle => <option key={cycle.id} value={cycle.id}>{cycle.name} {cycle.year}</option>)}
        </select>
        <select value={goalForm.employee} onChange={e => setGoalForm({ ...goalForm, employee: e.target.value })} required>
          <option value="">Select employee</option>
          {employeeOptions.map(emp => <option key={emp.id} value={emp.id}>{emp.label}</option>)}
        </select>
        <input placeholder="Goal title" value={goalForm.title} onChange={e => setGoalForm({ ...goalForm, title: e.target.value })} required />
        <select value={goalForm.category} onChange={e => setGoalForm({ ...goalForm, category: e.target.value })}>{goalCategories.map(category => <option key={category} value={category}>{category}</option>)}</select>
        <input type="number" step="0.01" placeholder="Weightage" value={goalForm.weightage} onChange={e => setGoalForm({ ...goalForm, weightage: e.target.value })} />
        <input placeholder="Target" value={goalForm.target_value} onChange={e => setGoalForm({ ...goalForm, target_value: e.target.value })} />
        <input placeholder="Unit" value={goalForm.measurement_unit} onChange={e => setGoalForm({ ...goalForm, measurement_unit: e.target.value })} />
        <input type="date" value={goalForm.due_date} onChange={e => setGoalForm({ ...goalForm, due_date: e.target.value })} />
        <textarea placeholder="Goal description" value={goalForm.description} onChange={e => setGoalForm({ ...goalForm, description: e.target.value })} />
        <button>Create Goal</button>
      </form>

      <h3>Goals / KRAs</h3>
      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'cycle_name', label: 'Cycle' },
        { key: 'title', label: 'Goal' },
        { key: 'category', label: 'Category' },
        { key: 'weightage', label: 'Weightage' },
        { key: 'status', label: 'Status' },
        { key: 'self_rating', label: 'Self Rating' },
        { key: 'manager_rating', label: 'Manager Rating' },
        { key: 'actions', label: 'Actions', render: row => (
          <div className="actions">
            {['DRAFT', 'REJECTED'].includes(row.status) && <button onClick={() => action(`/performance-goals/${row.id}/submit/`, 'Goal submitted.')}>Submit</button>}
            {canReviewTeam && row.status === 'SUBMITTED' && <button onClick={() => action(`/performance-goals/${row.id}/approve/`, 'Goal approved.')}>Approve</button>}
            {canReviewTeam && row.status === 'SUBMITTED' && <button className="dangerBtn" onClick={() => rejectGoal(row)}>Reject</button>}
            {row.status === 'APPROVED' && <button onClick={() => setGoalReviewForm(current => ({ ...current, goalId: row.id }))}>Review</button>}
          </div>
        )}
      ]} rows={goals} />

      <h3>Goal Rating</h3>
      <div className="inlineForm wideForm announcementForm">
        <select value={goalReviewForm.goalId} onChange={e => setGoalReviewForm({ ...goalReviewForm, goalId: e.target.value })}>
          <option value="">Select goal</option>
          {goals.map(goal => <option key={goal.id} value={goal.id}>{goal.employee_name} - {goal.title}</option>)}
        </select>
        <input type="number" step="0.01" min="0" max="5" placeholder="Self rating" value={goalReviewForm.self_rating} onChange={e => setGoalReviewForm({ ...goalReviewForm, self_rating: e.target.value })} />
        <input placeholder="Self comment" value={goalReviewForm.self_comment} onChange={e => setGoalReviewForm({ ...goalReviewForm, self_comment: e.target.value })} />
        <button onClick={saveGoalSelfReview}>Save Self Goal Review</button>
        {canReviewTeam && <input type="number" step="0.01" min="0" max="5" placeholder="Manager rating" value={goalReviewForm.manager_rating} onChange={e => setGoalReviewForm({ ...goalReviewForm, manager_rating: e.target.value })} />}
        {canReviewTeam && <input placeholder="Manager comment" value={goalReviewForm.manager_comment} onChange={e => setGoalReviewForm({ ...goalReviewForm, manager_comment: e.target.value })} />}
        {canReviewTeam && <button onClick={saveGoalManagerReview}>Save Manager Goal Review</button>}
      </div>

      <h3>Create Review Record</h3>
      <form className="inlineForm wideForm" onSubmit={createReview}>
        <select value={reviewForm.cycle || selectedCycle} onChange={e => setReviewForm({ ...reviewForm, cycle: e.target.value })} required>
          <option value="">Select cycle</option>
          {cycles.map(cycle => <option key={cycle.id} value={cycle.id}>{cycle.name} {cycle.year}</option>)}
        </select>
        <select value={reviewForm.employee} onChange={e => setReviewForm({ ...reviewForm, employee: e.target.value })} required>
          <option value="">Select employee</option>
          {employeeOptions.map(emp => <option key={emp.id} value={emp.id}>{emp.label}</option>)}
        </select>
        <select value={reviewForm.manager} onChange={e => setReviewForm({ ...reviewForm, manager: e.target.value })}>
          <option value="">Auto manager</option>
          {employeeOptions.map(emp => <option key={emp.id} value={emp.id}>{emp.label}</option>)}
        </select>
        <button>Create Review</button>
      </form>

      <h3>Review Records</h3>
      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'cycle_name', label: 'Cycle' },
        { key: 'manager_name', label: 'Manager' },
        { key: 'status', label: 'Status' },
        { key: 'goals_count', label: 'Goals' },
        { key: 'approved_goals_count', label: 'Approved Goals' },
        { key: 'goal_weightage_total', label: 'Weightage' },
        { key: 'manager_rating', label: 'Manager Rating' },
        { key: 'final_rating', label: 'Final Rating' },
        { key: 'final_score', label: 'Final Score' },
        { key: 'actions', label: 'Actions', render: row => (
          <div className="actions">
            <button onClick={() => setSelfReviewForm(current => ({ ...current, reviewId: row.id }))}>Self</button>
            {canReviewTeam && <button onClick={() => setManagerReviewForm(current => ({ ...current, reviewId: row.id }))}>Manager</button>}
            {canManageHR && <button onClick={() => setFinalizeForm(current => ({ ...current, reviewId: row.id }))}>Finalize</button>}
          </div>
        )}
      ]} rows={reviews} />

      <h3>Self Review</h3>
      <form className="inlineForm wideForm announcementForm" onSubmit={submitSelfReview}>
        <select value={selfReviewForm.reviewId} onChange={e => setSelfReviewForm({ ...selfReviewForm, reviewId: e.target.value })} required>
          <option value="">Select review</option>
          {reviews.map(review => <option key={review.id} value={review.id}>{review.employee_name} - {review.cycle_name}</option>)}
        </select>
        <textarea placeholder="Self summary" value={selfReviewForm.self_summary} onChange={e => setSelfReviewForm({ ...selfReviewForm, self_summary: e.target.value })} required />
        <textarea placeholder="Strengths" value={selfReviewForm.strengths} onChange={e => setSelfReviewForm({ ...selfReviewForm, strengths: e.target.value })} />
        <textarea placeholder="Improvement areas" value={selfReviewForm.improvement_areas} onChange={e => setSelfReviewForm({ ...selfReviewForm, improvement_areas: e.target.value })} />
        <textarea placeholder="Career goals" value={selfReviewForm.career_goals} onChange={e => setSelfReviewForm({ ...selfReviewForm, career_goals: e.target.value })} />
        <button>Submit Self Review</button>
      </form>

      {canReviewTeam && (
        <>
          <h3>Manager Review</h3>
          <form className="inlineForm wideForm announcementForm" onSubmit={submitManagerReview}>
            <select value={managerReviewForm.reviewId} onChange={e => setManagerReviewForm({ ...managerReviewForm, reviewId: e.target.value })} required>
              <option value="">Select review</option>
              {reviews.map(review => <option key={review.id} value={review.id}>{review.employee_name} - {review.cycle_name}</option>)}
            </select>
            <input type="number" min="0" max="5" step="0.01" placeholder="Manager rating" value={managerReviewForm.manager_rating} onChange={e => setManagerReviewForm({ ...managerReviewForm, manager_rating: e.target.value })} required />
            <textarea placeholder="Manager summary" value={managerReviewForm.manager_summary} onChange={e => setManagerReviewForm({ ...managerReviewForm, manager_summary: e.target.value })} required />
            <button>Submit Manager Review</button>
          </form>
        </>
      )}

      {canManageHR && (
        <>
          <h3>HR Finalization</h3>
          <form className="inlineForm wideForm announcementForm" onSubmit={finalizeReview}>
            <select value={finalizeForm.reviewId} onChange={e => setFinalizeForm({ ...finalizeForm, reviewId: e.target.value })} required>
              <option value="">Select review</option>
              {reviews.map(review => <option key={review.id} value={review.id}>{review.employee_name} - {review.cycle_name}</option>)}
            </select>
            <input type="number" min="0" max="5" step="0.01" placeholder="Final rating" value={finalizeForm.final_rating} onChange={e => setFinalizeForm({ ...finalizeForm, final_rating: e.target.value })} required />
            <input type="number" min="0" max="100" step="0.01" placeholder="Final score" value={finalizeForm.final_score} onChange={e => setFinalizeForm({ ...finalizeForm, final_score: e.target.value })} required />
            <textarea placeholder="HR comments" value={finalizeForm.hr_comments} onChange={e => setFinalizeForm({ ...finalizeForm, hr_comments: e.target.value })} />
            <button>Finalize Review</button>
          </form>
        </>
      )}
    </section>
  )
}
