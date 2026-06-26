import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { HR_ROLES, PAYROLL_ROLES, hasRole } from '../utils/roles.js'

const initialCaseForm = {
  employee: '',
  exit_type: 'RESIGNATION',
  resignation_date: '',
  requested_last_working_day: '',
  notice_period_days: '',
  reason: '',
  employee_notes: ''
}

const initialSettlementForm = {
  case: '',
  salary_days: '',
  basic_pay: '',
  leave_encashment: '',
  bonus: '',
  expense_reimbursement: '',
  notice_recovery: '',
  asset_recovery: '',
  tax_deduction: '',
  other_deductions: '',
  notes: ''
}

export default function Offboarding() {
  const { user } = useAuth()
  const canManageHR = hasRole(user, HR_ROLES)
  const canManageSettlement = hasRole(user, [...HR_ROLES, ...PAYROLL_ROLES])
  const [cases, setCases] = useState([])
  const [tasks, setTasks] = useState([])
  const [settlements, setSettlements] = useState([])
  const [documents, setDocuments] = useState([])
  const [employees, setEmployees] = useState([])
  const [caseForm, setCaseForm] = useState(initialCaseForm)
  const [settlementForm, setSettlementForm] = useState(initialSettlementForm)
  const [docForm, setDocForm] = useState({ case: '', title: '', document_type: 'RESIGNATION', notes: '' })
  const [file, setFile] = useState(null)
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
      api.get('/offboarding-cases/'),
      api.get('/offboarding-clearance/'),
      api.get('/final-settlements/'),
      api.get('/offboarding-documents/')
    ]
    if (canManageHR) requests.push(api.get('/employees/'))
    const responses = await Promise.all(requests)
    setCases(normalize(responses[0].data))
    setTasks(normalize(responses[1].data))
    setSettlements(normalize(responses[2].data))
    setDocuments(normalize(responses[3].data))
    if (canManageHR) setEmployees(normalize(responses[4].data))
  }

  useEffect(() => { load().catch(showError) }, [])

  const createCase = async (e) => {
    e.preventDefault()
    try {
      const payload = { ...caseForm }
      if (!payload.employee) delete payload.employee
      if (!payload.resignation_date) payload.resignation_date = null
      if (!payload.requested_last_working_day) payload.requested_last_working_day = null
      if (!payload.notice_period_days) payload.notice_period_days = 0
      await api.post('/offboarding-cases/', payload)
      setCaseForm(initialCaseForm)
      await load()
      showMessage('Offboarding case created. Submit it to start approval workflow.')
    } catch (err) {
      showError(err)
    }
  }

  const caseAction = async (row, action, payload = {}) => {
    try {
      await api.post(`/offboarding-cases/${row.id}/${action}/`, payload)
      await load()
      showMessage('Offboarding case updated.')
    } catch (err) {
      showError(err)
    }
  }

  const approveCase = async (row) => {
    const approved_last_working_day = window.prompt('Approved last working day YYYY-MM-DD', row.requested_last_working_day || '') || row.requested_last_working_day
    const notes = window.prompt('HR approval notes') || ''
    await caseAction(row, 'approve', { approved_last_working_day, notes, notice_period_days: row.notice_period_days || 0 })
  }

  const rejectCase = async (row) => {
    const reason = window.prompt('Reason') || ''
    await caseAction(row, 'reject', { reason })
  }

  const cancelCase = async (row) => {
    const reason = window.prompt('Cancellation reason') || ''
    await caseAction(row, 'cancel', { reason })
  }

  const taskAction = async (row, action) => {
    const remarks = window.prompt('Remarks') || ''
    try {
      await api.post(`/offboarding-clearance/${row.id}/${action}/`, { remarks })
      await load()
      showMessage('Clearance task updated.')
    } catch (err) {
      showError(err)
    }
  }

  const saveSettlement = async (e) => {
    e.preventDefault()
    try {
      const payload = { ...settlementForm }
      const moneyFields = ['salary_days', 'basic_pay', 'leave_encashment', 'bonus', 'expense_reimbursement', 'notice_recovery', 'asset_recovery', 'tax_deduction', 'other_deductions']
      moneyFields.forEach(field => { if (!payload[field]) payload[field] = 0 })
      const existing = settlements.find(item => String(item.case) === String(payload.case))
      if (existing) await api.patch(`/final-settlements/${existing.id}/`, payload)
      else await api.post('/final-settlements/', payload)
      setSettlementForm(initialSettlementForm)
      await load()
      showMessage('Final settlement saved.')
    } catch (err) {
      showError(err)
    }
  }

  const approveSettlement = async (row) => {
    try {
      await api.post(`/final-settlements/${row.id}/approve/`)
      await load()
      showMessage('Final settlement approved.')
    } catch (err) {
      showError(err)
    }
  }

  const markSettlementPaid = async (row) => {
    const payment_reference = window.prompt('Payment reference') || ''
    try {
      await api.post(`/final-settlements/${row.id}/mark-paid/`, { payment_reference })
      await load()
      showMessage('Final settlement marked as paid.')
    } catch (err) {
      showError(err)
    }
  }

  const uploadDocument = async (e) => {
    e.preventDefault()
    try {
      const formData = new FormData()
      Object.entries(docForm).forEach(([key, value]) => formData.append(key, value))
      if (file) formData.append('file', file)
      await api.post('/offboarding-documents/', formData)
      setDocForm({ case: '', title: '', document_type: 'RESIGNATION', notes: '' })
      setFile(null)
      const input = document.getElementById('offboardingDocFile')
      if (input) input.value = ''
      await load()
      showMessage('Offboarding document uploaded.')
    } catch (err) {
      showError(err)
    }
  }

  const downloadDocument = async (row) => {
    try {
      const res = await api.get(`/offboarding-documents/${row.id}/download/`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', row.file_name || `offboarding-document-${row.id}`)
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
      <PageHeader title="Offboarding" subtitle="Manage resignation, termination, clearance, final settlement, asset return, documents, and login deactivation." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="infoCard">
        Workflow: create case → submit → HR approval → clearance tasks → final settlement → completion → deactivate login.
      </div>

      <h3>1. Create Offboarding Case</h3>
      <form className="inlineForm wideForm" onSubmit={createCase}>
        {canManageHR && (
          <select value={caseForm.employee} onChange={e => setCaseForm({ ...caseForm, employee: e.target.value })} required>
            <option value="">Employee</option>
            {employees.map(emp => <option key={emp.id} value={emp.id}>{emp.full_name} - {emp.employee_code}</option>)}
          </select>
        )}
        <select value={caseForm.exit_type} onChange={e => setCaseForm({ ...caseForm, exit_type: e.target.value })}>
          <option value="RESIGNATION">Resignation</option>
          <option value="TERMINATION">Termination</option>
          <option value="END_OF_CONTRACT">End of Contract</option>
          <option value="RETIREMENT">Retirement</option>
          <option value="OTHER">Other</option>
        </select>
        <input type="date" value={caseForm.resignation_date} onChange={e => setCaseForm({ ...caseForm, resignation_date: e.target.value })} />
        <input type="date" value={caseForm.requested_last_working_day} onChange={e => setCaseForm({ ...caseForm, requested_last_working_day: e.target.value })} />
        <input type="number" placeholder="Notice period days" value={caseForm.notice_period_days} onChange={e => setCaseForm({ ...caseForm, notice_period_days: e.target.value })} />
        <input placeholder="Reason" value={caseForm.reason} onChange={e => setCaseForm({ ...caseForm, reason: e.target.value })} />
        <input placeholder="Employee notes" value={caseForm.employee_notes} onChange={e => setCaseForm({ ...caseForm, employee_notes: e.target.value })} />
        <button>Create Case</button>
      </form>

      <h3>2. Offboarding Cases</h3>
      <DataTable columns={[
        { key: 'employee_code', label: 'Code' },
        { key: 'employee_name', label: 'Employee' },
        { key: 'department_name', label: 'Department' },
        { key: 'exit_type', label: 'Type' },
        { key: 'status', label: 'Status' },
        { key: 'requested_last_working_day', label: 'Requested LWD' },
        { key: 'approved_last_working_day', label: 'Approved LWD' },
        { key: 'clearance_pending', label: 'Pending Clearance' },
        { key: 'assigned_assets_count', label: 'Assigned Assets' },
        { key: 'final_settlement_status', label: 'Settlement' },
        { key: 'final_net_payable', label: 'Net Payable' },
        { key: 'actions', label: 'Actions', render: row => (
          <div className="actions">
            {row.status === 'DRAFT' && <button onClick={() => caseAction(row, 'submit')}>Submit</button>}
            {canManageHR && ['SUBMITTED', 'HR_REVIEW', 'REJECTED'].includes(row.status) && <button onClick={() => approveCase(row)}>Approve</button>}
            {canManageHR && ['SUBMITTED', 'HR_REVIEW'].includes(row.status) && <button onClick={() => rejectCase(row)}>Reject</button>}
            {canManageHR && !['COMPLETED', 'CANCELLED'].includes(row.status) && <button onClick={() => cancelCase(row)}>Cancel</button>}
            {canManageHR && row.status === 'FINAL_SETTLEMENT' && <button onClick={() => caseAction(row, 'complete')}>Complete</button>}
            {canManageHR && row.status === 'COMPLETED' && !row.login_deactivated_at && <button className="dangerBtn" onClick={() => caseAction(row, 'deactivate-login')}>Deactivate Login</button>}
          </div>
        ) }
      ]} rows={cases} />

      <h3>3. Clearance Tasks</h3>
      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'department', label: 'Department' },
        { key: 'title', label: 'Task' },
        { key: 'status', label: 'Status' },
        { key: 'due_date', label: 'Due' },
        { key: 'assigned_to_email', label: 'Assigned To' },
        { key: 'remarks', label: 'Remarks' },
        { key: 'actions', label: 'Actions', render: row => row.status === 'PENDING' ? (
          <div className="actions">
            <button onClick={() => taskAction(row, 'clear')}>Clear</button>
            <button onClick={() => taskAction(row, 'waive')}>Waive</button>
            <button className="dangerBtn" onClick={() => taskAction(row, 'reject')}>Reject</button>
          </div>
        ) : '-' }
      ]} rows={tasks} />

      {canManageSettlement && (
        <>
          <h3>4. Final Settlement</h3>
          <form className="inlineForm wideForm" onSubmit={saveSettlement}>
            <select value={settlementForm.case} onChange={e => setSettlementForm({ ...settlementForm, case: e.target.value })} required>
              <option value="">Offboarding case</option>
              {cases.map(item => <option key={item.id} value={item.id}>{item.employee_code} - {item.employee_name}</option>)}
            </select>
            <input type="number" step="0.01" placeholder="Salary days" value={settlementForm.salary_days} onChange={e => setSettlementForm({ ...settlementForm, salary_days: e.target.value })} />
            <input type="number" step="0.01" placeholder="Basic pay" value={settlementForm.basic_pay} onChange={e => setSettlementForm({ ...settlementForm, basic_pay: e.target.value })} />
            <input type="number" step="0.01" placeholder="Leave encashment" value={settlementForm.leave_encashment} onChange={e => setSettlementForm({ ...settlementForm, leave_encashment: e.target.value })} />
            <input type="number" step="0.01" placeholder="Bonus" value={settlementForm.bonus} onChange={e => setSettlementForm({ ...settlementForm, bonus: e.target.value })} />
            <input type="number" step="0.01" placeholder="Expense reimbursement" value={settlementForm.expense_reimbursement} onChange={e => setSettlementForm({ ...settlementForm, expense_reimbursement: e.target.value })} />
            <input type="number" step="0.01" placeholder="Notice recovery" value={settlementForm.notice_recovery} onChange={e => setSettlementForm({ ...settlementForm, notice_recovery: e.target.value })} />
            <input type="number" step="0.01" placeholder="Asset recovery" value={settlementForm.asset_recovery} onChange={e => setSettlementForm({ ...settlementForm, asset_recovery: e.target.value })} />
            <input type="number" step="0.01" placeholder="Tax deduction" value={settlementForm.tax_deduction} onChange={e => setSettlementForm({ ...settlementForm, tax_deduction: e.target.value })} />
            <input type="number" step="0.01" placeholder="Other deductions" value={settlementForm.other_deductions} onChange={e => setSettlementForm({ ...settlementForm, other_deductions: e.target.value })} />
            <input placeholder="Notes" value={settlementForm.notes} onChange={e => setSettlementForm({ ...settlementForm, notes: e.target.value })} />
            <button>Save Settlement</button>
          </form>
          <DataTable columns={[
            { key: 'employee_code', label: 'Code' },
            { key: 'employee_name', label: 'Employee' },
            { key: 'status', label: 'Status' },
            { key: 'basic_pay', label: 'Basic' },
            { key: 'leave_encashment', label: 'Leave Encashment' },
            { key: 'notice_recovery', label: 'Notice Recovery' },
            { key: 'asset_recovery', label: 'Asset Recovery' },
            { key: 'net_payable', label: 'Net Payable' },
            { key: 'payment_reference', label: 'Payment Ref' },
            { key: 'actions', label: 'Actions', render: row => (
              <div className="actions">
                {row.status === 'DRAFT' && <button onClick={() => approveSettlement(row)}>Approve</button>}
                {row.status === 'APPROVED' && <button onClick={() => markSettlementPaid(row)}>Mark Paid</button>}
              </div>
            ) }
          ]} rows={settlements} />
        </>
      )}

      <h3>{canManageSettlement ? '5.' : '4.'} Offboarding Documents</h3>
      <form className="inlineForm wideForm" onSubmit={uploadDocument}>
        <select value={docForm.case} onChange={e => setDocForm({ ...docForm, case: e.target.value })} required>
          <option value="">Offboarding case</option>
          {cases.map(item => <option key={item.id} value={item.id}>{item.employee_code} - {item.employee_name}</option>)}
        </select>
        <input placeholder="Title" value={docForm.title} onChange={e => setDocForm({ ...docForm, title: e.target.value })} required />
        <select value={docForm.document_type} onChange={e => setDocForm({ ...docForm, document_type: e.target.value })}>
          <option value="RESIGNATION">Resignation</option>
          <option value="RELIEVING">Relieving Letter</option>
          <option value="EXPERIENCE">Experience Letter</option>
          <option value="SETTLEMENT">Settlement</option>
          <option value="CLEARANCE">Clearance</option>
          <option value="OTHER">Other</option>
        </select>
        <input placeholder="Notes" value={docForm.notes} onChange={e => setDocForm({ ...docForm, notes: e.target.value })} />
        <input id="offboardingDocFile" type="file" onChange={e => setFile(e.target.files?.[0] || null)} required />
        <button>Upload Document</button>
      </form>
      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'title', label: 'Title' },
        { key: 'document_type', label: 'Type' },
        { key: 'file_name', label: 'File' },
        { key: 'size', label: 'Size' },
        { key: 'uploaded_by_email', label: 'Uploaded By' },
        { key: 'actions', label: 'Actions', render: row => <button onClick={() => downloadDocument(row)}>Download</button> }
      ]} rows={documents} />
    </section>
  )
}
