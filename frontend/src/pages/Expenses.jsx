import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { HR_ROLES, MANAGER_ROLES, PAYROLL_ROLES, hasRole } from '../utils/roles.js'

export default function Expenses() {
  const { user } = useAuth()
  const [expenses, setExpenses] = useState([])
  const [categories, setCategories] = useState([])
  const [employees, setEmployees] = useState([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [receipt, setReceipt] = useState(null)

  const canManageCategories = hasRole(user, HR_ROLES)
  const canApprove = hasRole(user, MANAGER_ROLES)
  const canPay = hasRole(user, PAYROLL_ROLES)

  const [categoryForm, setCategoryForm] = useState({ name: '', description: '' })
  const [expenseForm, setExpenseForm] = useState({
    employee: '',
    category: '',
    title: '',
    expense_date: '',
    amount: '',
    currency: 'INR',
    description: ''
  })
  const [paymentForm, setPaymentForm] = useState({ payment_mode: 'BANK_TRANSFER', payment_reference: '', finance_notes: '' })

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
    const [expenseRes, categoryRes, employeeRes] = await Promise.all([
      api.get('/expenses/'),
      api.get('/expense-categories/'),
      api.get('/employees/')
    ])
    const empRows = normalize(employeeRes.data)
    setExpenses(normalize(expenseRes.data))
    setCategories(normalize(categoryRes.data))
    setEmployees(empRows)
    if (!expenseForm.employee && empRows.length === 1) {
      setExpenseForm(current => ({ ...current, employee: String(empRows[0].id) }))
    }
  }

  useEffect(() => { load().catch(showError) }, [])

  const createCategory = async (e) => {
    e.preventDefault()
    try {
      await api.post('/expense-categories/', categoryForm)
      setCategoryForm({ name: '', description: '' })
      await load()
      showMessage('Expense category created.')
    } catch (err) {
      showError(err)
    }
  }

  const createExpense = async (e) => {
    e.preventDefault()
    try {
      const formData = new FormData()
      Object.entries(expenseForm).forEach(([key, value]) => {
        if (value !== '') formData.append(key, value)
      })
      if (receipt) formData.append('receipt', receipt)
      await api.post('/expenses/', formData)
      setExpenseForm({ employee: employees.length === 1 ? String(employees[0].id) : '', category: '', title: '', expense_date: '', amount: '', currency: 'INR', description: '' })
      setReceipt(null)
      const receiptInput = document.getElementById('expenseReceipt')
      if (receiptInput) receiptInput.value = ''
      await load()
      showMessage('Expense submitted successfully.')
    } catch (err) {
      showError(err)
    }
  }

  const expenseAction = async (row, action, body = {}) => {
    try {
      const res = await api.post(`/expenses/${row.id}/${action}/`, body)
      await load()
      showMessage(res.data.detail || 'Expense action completed.')
    } catch (err) {
      showError(err)
    }
  }

  const rejectExpense = async (row) => {
    const reason = window.prompt('Reason for rejection') || ''
    expenseAction(row, 'reject', { reason })
  }

  const markPaid = async (row) => {
    expenseAction(row, 'mark-paid', paymentForm)
  }

  const downloadReceipt = async (row) => {
    try {
      const res = await api.get(`/expenses/${row.id}/download-receipt/`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', row.receipt_file_name || `expense-${row.id}-receipt`)
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
      <PageHeader title="Expenses" subtitle="Submit reimbursements, approve claims, and mark approved expenses as paid." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="infoCard">
        Expense flow: employee submits claim with receipt → manager/HR approves or rejects → payroll/finance marks approved expense as paid.
      </div>

      {canManageCategories && (
        <>
          <h3>1. Expense Categories</h3>
          <form className="inlineForm wideForm" onSubmit={createCategory}>
            <input placeholder="Category name" value={categoryForm.name} onChange={e => setCategoryForm({ ...categoryForm, name: e.target.value })} required />
            <input placeholder="Description" value={categoryForm.description} onChange={e => setCategoryForm({ ...categoryForm, description: e.target.value })} />
            <button>Create Category</button>
          </form>
          <DataTable columns={[
            { key: 'name', label: 'Category' },
            { key: 'description', label: 'Description' },
            { key: 'is_active', label: 'Active', render: row => row.is_active ? 'Yes' : 'No' }
          ]} rows={categories} />
        </>
      )}

      <h3>{canManageCategories ? '2.' : '1.'} Submit Expense</h3>
      <form className="inlineForm wideForm" onSubmit={createExpense}>
        <select value={expenseForm.employee} onChange={e => setExpenseForm({ ...expenseForm, employee: e.target.value })} required>
          <option value="">Employee</option>
          {employees.map(emp => <option key={emp.id} value={emp.id}>{emp.full_name} - {emp.employee_code}</option>)}
        </select>
        <select value={expenseForm.category} onChange={e => setExpenseForm({ ...expenseForm, category: e.target.value })}>
          <option value="">Category</option>
          {categories.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}
        </select>
        <input placeholder="Title" value={expenseForm.title} onChange={e => setExpenseForm({ ...expenseForm, title: e.target.value })} required />
        <input type="date" value={expenseForm.expense_date} onChange={e => setExpenseForm({ ...expenseForm, expense_date: e.target.value })} required />
        <input type="number" step="0.01" placeholder="Amount" value={expenseForm.amount} onChange={e => setExpenseForm({ ...expenseForm, amount: e.target.value })} required />
        <input placeholder="Currency" value={expenseForm.currency} onChange={e => setExpenseForm({ ...expenseForm, currency: e.target.value.toUpperCase() })} />
        <input placeholder="Description" value={expenseForm.description} onChange={e => setExpenseForm({ ...expenseForm, description: e.target.value })} />
        <input id="expenseReceipt" type="file" onChange={e => setReceipt(e.target.files?.[0] || null)} />
        <button>Submit Expense</button>
      </form>

      {canPay && (
        <div className="infoCard">
          <strong>Payment defaults:</strong>
          <div className="miniAction" style={{ marginTop: 10 }}>
            <select value={paymentForm.payment_mode} onChange={e => setPaymentForm({ ...paymentForm, payment_mode: e.target.value })}>
              <option value="BANK_TRANSFER">Bank Transfer</option>
              <option value="CASH">Cash</option>
              <option value="UPI">UPI</option>
              <option value="CHEQUE">Cheque</option>
              <option value="OTHER">Other</option>
            </select>
            <input placeholder="Payment reference" value={paymentForm.payment_reference} onChange={e => setPaymentForm({ ...paymentForm, payment_reference: e.target.value })} />
            <input placeholder="Finance notes" value={paymentForm.finance_notes} onChange={e => setPaymentForm({ ...paymentForm, finance_notes: e.target.value })} />
          </div>
        </div>
      )}

      <h3>{canManageCategories ? '3.' : '2.'} Expense Claims</h3>
      <DataTable columns={[
        { key: 'claim_number', label: 'Claim No.' },
        { key: 'employee_name', label: 'Employee' },
        { key: 'category_name', label: 'Category' },
        { key: 'title', label: 'Title' },
        { key: 'expense_date', label: 'Date' },
        { key: 'amount', label: 'Amount', render: row => `${row.currency} ${row.amount}` },
        { key: 'status', label: 'Status' },
        { key: 'payment_reference', label: 'Payment Ref.' },
        { key: 'actions', label: 'Actions', render: row => (
          <div className="actions">
            {row.receipt_download_url && <button onClick={() => downloadReceipt(row)}>Receipt</button>}
            {canApprove && row.status === 'SUBMITTED' && <button onClick={() => expenseAction(row, 'approve')}>Approve</button>}
            {canApprove && ['SUBMITTED', 'APPROVED'].includes(row.status) && <button className="dangerBtn" onClick={() => rejectExpense(row)}>Reject</button>}
            {canPay && row.status === 'APPROVED' && <button onClick={() => markPaid(row)}>Mark Paid</button>}
          </div>
        ) }
      ]} rows={expenses} />
    </section>
  )
}
