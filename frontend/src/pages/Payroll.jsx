import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'

const currentYear = new Date().getFullYear()
const currentMonth = new Date().getMonth() + 1

export default function Payroll() {
  const [employees, setEmployees] = useState([])
  const [components, setComponents] = useState([])
  const [salaryComponents, setSalaryComponents] = useState([])
  const [runs, setRuns] = useState([])
  const [payslips, setPayslips] = useState([])
  const [selectedRun, setSelectedRun] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const [componentForm, setComponentForm] = useState({
    name: '',
    component_type: 'EARNING',
    calculation_type: 'FIXED',
    default_amount: '',
    default_percent: '',
    is_taxable: true,
    is_active: true
  })
  const [salaryForm, setSalaryForm] = useState({
    employee: '',
    component: '',
    amount: '',
    percent: '',
    effective_from: '',
    effective_to: '',
    is_active: true
  })
  const [runForm, setRunForm] = useState({ month: String(currentMonth), year: String(currentYear), notes: '' })

  const showError = (err) => {
    setMessage('')
    setError(err?.response?.data?.detail || JSON.stringify(err?.response?.data || {}) || 'Something went wrong')
  }

  const showMessage = (text) => {
    setError('')
    setMessage(text)
  }

  const load = async () => {
    const [empRes, compRes, salaryRes, runRes, slipRes] = await Promise.all([
      api.get('/employees/'),
      api.get('/payroll-components/'),
      api.get('/salary-components/'),
      api.get('/payroll-runs/'),
      api.get('/payslips/')
    ])
    setEmployees(empRes.data.results || empRes.data)
    setComponents(compRes.data.results || compRes.data)
    setSalaryComponents(salaryRes.data.results || salaryRes.data)
    setRuns(runRes.data.results || runRes.data)
    setPayslips(slipRes.data.results || slipRes.data)
  }

  useEffect(() => { load().catch(showError) }, [])

  const createComponent = async (e) => {
    e.preventDefault()
    try {
      await api.post('/payroll-components/', { ...componentForm, default_amount: componentForm.default_amount || '0', default_percent: componentForm.default_percent || '0' })
      setComponentForm({ name: '', component_type: 'EARNING', calculation_type: 'FIXED', default_amount: '', default_percent: '', is_taxable: true, is_active: true })
      await load()
      showMessage('Payroll component created.')
    } catch (err) {
      showError(err)
    }
  }

  const assignSalaryComponent = async (e) => {
    e.preventDefault()
    try {
      await api.post('/salary-components/', { ...salaryForm, amount: salaryForm.amount || '0', percent: salaryForm.percent || '0', effective_from: salaryForm.effective_from || null, effective_to: salaryForm.effective_to || null })
      setSalaryForm({ employee: '', component: '', amount: '', percent: '', effective_from: '', effective_to: '', is_active: true })
      await load()
      showMessage('Salary component assigned.')
    } catch (err) {
      showError(err)
    }
  }

  const createRun = async (e) => {
    e.preventDefault()
    try {
      await api.post('/payroll-runs/', runForm)
      setRunForm({ month: String(currentMonth), year: String(currentYear), notes: '' })
      await load()
      showMessage('Payroll run created.')
    } catch (err) {
      showError(err)
    }
  }

  const runAction = async (run, action) => {
    try {
      const res = await api.post(`/payroll-runs/${run.id}/${action}/`)
      await load()
      showMessage(res.data.detail || 'Payroll action completed.')
    } catch (err) {
      showError(err)
    }
  }

  const viewPayslips = async (run) => {
    try {
      const res = await api.get(`/payroll-runs/${run.id}/payslips/`)
      setSelectedRun(run)
      setPayslips(res.data.results || res.data)
      showMessage(`Showing payslips for ${run.month}/${run.year}.`)
    } catch (err) {
      showError(err)
    }
  }

  return (
    <section>
      <PageHeader title="Payroll" subtitle="Generate payslips from attendance, leaves, overtime, salary components, and deductions" />

      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="infoCard">
        Payroll flow: create components → assign components to employees → create monthly payroll run → generate payslips → approve → mark paid.
      </div>

      <h3>1. Payroll Components</h3>
      <form className="inlineForm wideForm" onSubmit={createComponent}>
        <input placeholder="Component name" value={componentForm.name} onChange={e => setComponentForm({ ...componentForm, name: e.target.value })} />
        <select value={componentForm.component_type} onChange={e => setComponentForm({ ...componentForm, component_type: e.target.value })}>
          <option value="EARNING">Earning</option>
          <option value="DEDUCTION">Deduction</option>
        </select>
        <select value={componentForm.calculation_type} onChange={e => setComponentForm({ ...componentForm, calculation_type: e.target.value })}>
          <option value="FIXED">Fixed Amount</option>
          <option value="PERCENT_BASIC">Percent of Basic</option>
          <option value="PERCENT_GROSS">Percent of Gross</option>
        </select>
        <input placeholder="Default amount" value={componentForm.default_amount} onChange={e => setComponentForm({ ...componentForm, default_amount: e.target.value })} />
        <input placeholder="Default percent" value={componentForm.default_percent} onChange={e => setComponentForm({ ...componentForm, default_percent: e.target.value })} />
        <label className="checkLabel"><input type="checkbox" checked={componentForm.is_taxable} onChange={e => setComponentForm({ ...componentForm, is_taxable: e.target.checked })} /> Taxable</label>
        <button>Create Component</button>
      </form>
      <DataTable columns={[
        { key: 'name', label: 'Name' },
        { key: 'component_type', label: 'Type' },
        { key: 'calculation_type', label: 'Calculation' },
        { key: 'default_amount', label: 'Amount' },
        { key: 'default_percent', label: 'Percent' },
        { key: 'is_active', label: 'Active', render: r => r.is_active ? 'Yes' : 'No' }
      ]} rows={components} />

      <h3>2. Employee Salary Components</h3>
      <form className="inlineForm wideForm" onSubmit={assignSalaryComponent}>
        <select value={salaryForm.employee} onChange={e => setSalaryForm({ ...salaryForm, employee: e.target.value })}>
          <option value="">Employee</option>
          {employees.map(e => <option key={e.id} value={e.id}>{e.full_name} - {e.employee_code}</option>)}
        </select>
        <select value={salaryForm.component} onChange={e => setSalaryForm({ ...salaryForm, component: e.target.value })}>
          <option value="">Component</option>
          {components.map(c => <option key={c.id} value={c.id}>{c.name} - {c.component_type}</option>)}
        </select>
        <input placeholder="Amount override" value={salaryForm.amount} onChange={e => setSalaryForm({ ...salaryForm, amount: e.target.value })} />
        <input placeholder="Percent override" value={salaryForm.percent} onChange={e => setSalaryForm({ ...salaryForm, percent: e.target.value })} />
        <input type="date" value={salaryForm.effective_from} onChange={e => setSalaryForm({ ...salaryForm, effective_from: e.target.value })} />
        <input type="date" value={salaryForm.effective_to} onChange={e => setSalaryForm({ ...salaryForm, effective_to: e.target.value })} />
        <button>Assign</button>
      </form>
      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'component_name', label: 'Component' },
        { key: 'component_type', label: 'Type' },
        { key: 'amount', label: 'Amount' },
        { key: 'percent', label: 'Percent' },
        { key: 'effective_from', label: 'From' },
        { key: 'effective_to', label: 'To' },
        { key: 'is_active', label: 'Active', render: r => r.is_active ? 'Yes' : 'No' }
      ]} rows={salaryComponents} />

      <h3>3. Payroll Runs</h3>
      <form className="inlineForm wideForm" onSubmit={createRun}>
        <input placeholder="Month" value={runForm.month} onChange={e => setRunForm({ ...runForm, month: e.target.value })} />
        <input placeholder="Year" value={runForm.year} onChange={e => setRunForm({ ...runForm, year: e.target.value })} />
        <input placeholder="Notes" value={runForm.notes} onChange={e => setRunForm({ ...runForm, notes: e.target.value })} />
        <button>Create Payroll Run</button>
      </form>
      <DataTable columns={[
        { key: 'month', label: 'Month' },
        { key: 'year', label: 'Year' },
        { key: 'status', label: 'Status' },
        { key: 'payslip_count', label: 'Payslips' },
        { key: 'total_gross', label: 'Gross' },
        { key: 'total_deductions', label: 'Deductions' },
        { key: 'total_net', label: 'Net' },
        { key: 'actions', label: 'Actions', render: r => (
          <div className="actions">
            <button onClick={() => runAction(r, 'generate')}>Generate</button>
            <button onClick={() => runAction(r, 'approve')}>Approve</button>
            <button onClick={() => runAction(r, 'mark-paid')}>Mark Paid</button>
            <button onClick={() => viewPayslips(r)}>View Payslips</button>
          </div>
        ) }
      ]} rows={runs} />

      <h3>{selectedRun ? `4. Payslips for ${selectedRun.month}/${selectedRun.year}` : '4. Payslips'}</h3>
      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'employee_code', label: 'Code' },
        { key: 'month', label: 'Month' },
        { key: 'year', label: 'Year' },
        { key: 'expected_work_days', label: 'Work Days' },
        { key: 'payable_days', label: 'Payable Days' },
        { key: 'loss_of_pay_days', label: 'LOP Days' },
        { key: 'basic', label: 'Basic' },
        { key: 'gross_earnings', label: 'Gross' },
        { key: 'total_deductions', label: 'Deductions' },
        { key: 'net_pay', label: 'Net Pay' },
        { key: 'status', label: 'Status' }
      ]} rows={payslips} />
    </section>
  )
}
