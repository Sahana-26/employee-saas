import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { ASSET_ROLES, hasRole } from '../utils/roles.js'

const emptyAsset = {
  category: '',
  asset_code: '',
  name: '',
  asset_type: 'LAPTOP',
  brand: '',
  model: '',
  serial_number: '',
  purchase_date: '',
  warranty_end_date: '',
  purchase_cost: '',
  vendor: '',
  location: '',
  notes: ''
}

export default function Assets() {
  const { user } = useAuth()
  const canManage = hasRole(user, ASSET_ROLES)
  const [assets, setAssets] = useState([])
  const [categories, setCategories] = useState([])
  const [employees, setEmployees] = useState([])
  const [assignments, setAssignments] = useState([])
  const [documents, setDocuments] = useState([])
  const [maintenance, setMaintenance] = useState([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [file, setFile] = useState(null)
  const [categoryForm, setCategoryForm] = useState({ name: '', description: '' })
  const [assetForm, setAssetForm] = useState(emptyAsset)
  const [assignForm, setAssignForm] = useState({ asset: '', employee: '', expected_return_date: '', condition_at_issue: '', issue_notes: '' })
  const [docForm, setDocForm] = useState({ asset: '', title: '', category: 'INVOICE', notes: '' })
  const [maintenanceForm, setMaintenanceForm] = useState({ asset: '', maintenance_type: '', status: 'OPEN', start_date: '', end_date: '', vendor: '', cost: '', notes: '' })

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
      api.get('/assets/'),
      api.get('/asset-categories/'),
      api.get('/asset-assignments/'),
      api.get('/asset-documents/'),
      api.get('/asset-maintenance/')
    ]
    if (canManage) requests.push(api.get('/employees/'))
    const responses = await Promise.all(requests)
    setAssets(normalize(responses[0].data))
    setCategories(normalize(responses[1].data))
    setAssignments(normalize(responses[2].data))
    setDocuments(normalize(responses[3].data))
    setMaintenance(normalize(responses[4].data))
    if (canManage) setEmployees(normalize(responses[5].data))
  }

  useEffect(() => { load().catch(showError) }, [])

  const createCategory = async (e) => {
    e.preventDefault()
    try {
      await api.post('/asset-categories/', categoryForm)
      setCategoryForm({ name: '', description: '' })
      await load()
      showMessage('Asset category created.')
    } catch (err) {
      showError(err)
    }
  }

  const createAsset = async (e) => {
    e.preventDefault()
    try {
      const payload = { ...assetForm }
      if (!payload.category) payload.category = null
      if (!payload.purchase_date) payload.purchase_date = null
      if (!payload.warranty_end_date) payload.warranty_end_date = null
      if (!payload.purchase_cost) payload.purchase_cost = 0
      await api.post('/assets/', payload)
      setAssetForm(emptyAsset)
      await load()
      showMessage('Asset created.')
    } catch (err) {
      showError(err)
    }
  }

  const assignAsset = async (e) => {
    e.preventDefault()
    try {
      const payload = { ...assignForm }
      if (!payload.expected_return_date) payload.expected_return_date = null
      await api.post(`/assets/${assignForm.asset}/assign/`, payload)
      setAssignForm({ asset: '', employee: '', expected_return_date: '', condition_at_issue: '', issue_notes: '' })
      await load()
      showMessage('Asset assigned.')
    } catch (err) {
      showError(err)
    }
  }

  const returnAsset = async (row) => {
    const condition = window.prompt('Condition at return') || ''
    try {
      await api.post(`/assets/${row.id}/return/`, { condition_at_return: condition, next_status: 'AVAILABLE' })
      await load()
      showMessage('Asset returned and marked available.')
    } catch (err) {
      showError(err)
    }
  }

  const changeStatus = async (row, action) => {
    const notes = window.prompt('Notes') || ''
    try {
      await api.post(`/assets/${row.id}/${action}/`, { notes })
      await load()
      showMessage('Asset status updated.')
    } catch (err) {
      showError(err)
    }
  }

  const uploadDocument = async (e) => {
    e.preventDefault()
    try {
      const formData = new FormData()
      Object.entries(docForm).forEach(([key, value]) => {
        if (value !== '') formData.append(key, value)
      })
      if (file) formData.append('file', file)
      await api.post('/asset-documents/', formData)
      setDocForm({ asset: '', title: '', category: 'INVOICE', notes: '' })
      setFile(null)
      const fileInput = document.getElementById('assetDocumentFile')
      if (fileInput) fileInput.value = ''
      await load()
      showMessage('Asset document uploaded.')
    } catch (err) {
      showError(err)
    }
  }

  const downloadDocument = async (row) => {
    try {
      const res = await api.get(`/asset-documents/${row.id}/download/`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', row.file_name || `asset-document-${row.id}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      showError(err)
    }
  }

  const createMaintenance = async (e) => {
    e.preventDefault()
    try {
      const payload = { ...maintenanceForm }
      if (!payload.end_date) payload.end_date = null
      if (!payload.cost) payload.cost = 0
      await api.post('/asset-maintenance/', payload)
      setMaintenanceForm({ asset: '', maintenance_type: '', status: 'OPEN', start_date: '', end_date: '', vendor: '', cost: '', notes: '' })
      await load()
      showMessage('Maintenance record created.')
    } catch (err) {
      showError(err)
    }
  }

  const availableAssets = assets.filter(asset => asset.status !== 'ASSIGNED' && asset.status !== 'LOST' && asset.status !== 'RETIRED')
  const assignedAssets = assets.filter(asset => asset.status === 'ASSIGNED')

  return (
    <section>
      <PageHeader title="Assets" subtitle="Manage IT inventory, asset assignments, returns, maintenance, and PostgreSQL-stored asset documents." />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="infoCard">
        Asset flow: IT/HR/Admin creates asset → assigns it to employee → tracks handover/return → uploads invoice/warranty/handover files → maintains status history.
      </div>

      {canManage && (
        <>
          <h3>1. Asset Categories</h3>
          <form className="inlineForm wideForm" onSubmit={createCategory}>
            <input placeholder="Category name" value={categoryForm.name} onChange={e => setCategoryForm({ ...categoryForm, name: e.target.value })} required />
            <input placeholder="Description" value={categoryForm.description} onChange={e => setCategoryForm({ ...categoryForm, description: e.target.value })} />
            <button>Create Category</button>
          </form>
          <DataTable columns={[
            { key: 'name', label: 'Category' },
            { key: 'description', label: 'Description' },
            { key: 'asset_count', label: 'Assets' },
            { key: 'is_active', label: 'Active', render: row => row.is_active ? 'Yes' : 'No' }
          ]} rows={categories} />

          <h3>2. Create Asset</h3>
          <form className="inlineForm wideForm" onSubmit={createAsset}>
            <select value={assetForm.category} onChange={e => setAssetForm({ ...assetForm, category: e.target.value })}>
              <option value="">Category</option>
              {categories.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select>
            <input placeholder="Asset code" value={assetForm.asset_code} onChange={e => setAssetForm({ ...assetForm, asset_code: e.target.value })} required />
            <input placeholder="Asset name" value={assetForm.name} onChange={e => setAssetForm({ ...assetForm, name: e.target.value })} required />
            <select value={assetForm.asset_type} onChange={e => setAssetForm({ ...assetForm, asset_type: e.target.value })}>
              <option value="LAPTOP">Laptop</option>
              <option value="DESKTOP">Desktop</option>
              <option value="MOBILE">Mobile</option>
              <option value="TABLET">Tablet</option>
              <option value="SIM">SIM Card</option>
              <option value="ACCESSORY">Accessory</option>
              <option value="SOFTWARE">Software License</option>
              <option value="NETWORK">Network Device</option>
              <option value="OTHER">Other</option>
            </select>
            <input placeholder="Brand" value={assetForm.brand} onChange={e => setAssetForm({ ...assetForm, brand: e.target.value })} />
            <input placeholder="Model" value={assetForm.model} onChange={e => setAssetForm({ ...assetForm, model: e.target.value })} />
            <input placeholder="Serial number" value={assetForm.serial_number} onChange={e => setAssetForm({ ...assetForm, serial_number: e.target.value })} />
            <input type="date" value={assetForm.purchase_date} onChange={e => setAssetForm({ ...assetForm, purchase_date: e.target.value })} />
            <input type="date" value={assetForm.warranty_end_date} onChange={e => setAssetForm({ ...assetForm, warranty_end_date: e.target.value })} />
            <input type="number" step="0.01" placeholder="Purchase cost" value={assetForm.purchase_cost} onChange={e => setAssetForm({ ...assetForm, purchase_cost: e.target.value })} />
            <input placeholder="Vendor" value={assetForm.vendor} onChange={e => setAssetForm({ ...assetForm, vendor: e.target.value })} />
            <input placeholder="Location" value={assetForm.location} onChange={e => setAssetForm({ ...assetForm, location: e.target.value })} />
            <input placeholder="Notes" value={assetForm.notes} onChange={e => setAssetForm({ ...assetForm, notes: e.target.value })} />
            <button>Create Asset</button>
          </form>

          <h3>3. Assign Asset</h3>
          <form className="inlineForm wideForm" onSubmit={assignAsset}>
            <select value={assignForm.asset} onChange={e => setAssignForm({ ...assignForm, asset: e.target.value })} required>
              <option value="">Available asset</option>
              {availableAssets.map(asset => <option key={asset.id} value={asset.id}>{asset.asset_code} - {asset.name}</option>)}
            </select>
            <select value={assignForm.employee} onChange={e => setAssignForm({ ...assignForm, employee: e.target.value })} required>
              <option value="">Employee</option>
              {employees.map(emp => <option key={emp.id} value={emp.id}>{emp.full_name} - {emp.employee_code}</option>)}
            </select>
            <input type="date" value={assignForm.expected_return_date} onChange={e => setAssignForm({ ...assignForm, expected_return_date: e.target.value })} />
            <input placeholder="Condition at issue" value={assignForm.condition_at_issue} onChange={e => setAssignForm({ ...assignForm, condition_at_issue: e.target.value })} />
            <input placeholder="Issue notes" value={assignForm.issue_notes} onChange={e => setAssignForm({ ...assignForm, issue_notes: e.target.value })} />
            <button>Assign Asset</button>
          </form>

          <h3>4. Upload Asset Document</h3>
          <form className="inlineForm wideForm" onSubmit={uploadDocument}>
            <select value={docForm.asset} onChange={e => setDocForm({ ...docForm, asset: e.target.value })} required>
              <option value="">Asset</option>
              {assets.map(asset => <option key={asset.id} value={asset.id}>{asset.asset_code} - {asset.name}</option>)}
            </select>
            <input placeholder="Document title" value={docForm.title} onChange={e => setDocForm({ ...docForm, title: e.target.value })} required />
            <select value={docForm.category} onChange={e => setDocForm({ ...docForm, category: e.target.value })}>
              <option value="INVOICE">Invoice</option>
              <option value="WARRANTY">Warranty</option>
              <option value="HANDOVER">Handover</option>
              <option value="PHOTO">Photo</option>
              <option value="OTHER">Other</option>
            </select>
            <input placeholder="Notes" value={docForm.notes} onChange={e => setDocForm({ ...docForm, notes: e.target.value })} />
            <input id="assetDocumentFile" type="file" onChange={e => setFile(e.target.files?.[0] || null)} required />
            <button>Upload Document</button>
          </form>

          <h3>5. Maintenance Record</h3>
          <form className="inlineForm wideForm" onSubmit={createMaintenance}>
            <select value={maintenanceForm.asset} onChange={e => setMaintenanceForm({ ...maintenanceForm, asset: e.target.value })} required>
              <option value="">Asset</option>
              {assets.map(asset => <option key={asset.id} value={asset.id}>{asset.asset_code} - {asset.name}</option>)}
            </select>
            <input placeholder="Maintenance type" value={maintenanceForm.maintenance_type} onChange={e => setMaintenanceForm({ ...maintenanceForm, maintenance_type: e.target.value })} required />
            <select value={maintenanceForm.status} onChange={e => setMaintenanceForm({ ...maintenanceForm, status: e.target.value })}>
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
            <input type="date" value={maintenanceForm.start_date} onChange={e => setMaintenanceForm({ ...maintenanceForm, start_date: e.target.value })} required />
            <input type="date" value={maintenanceForm.end_date} onChange={e => setMaintenanceForm({ ...maintenanceForm, end_date: e.target.value })} />
            <input placeholder="Vendor" value={maintenanceForm.vendor} onChange={e => setMaintenanceForm({ ...maintenanceForm, vendor: e.target.value })} />
            <input type="number" step="0.01" placeholder="Cost" value={maintenanceForm.cost} onChange={e => setMaintenanceForm({ ...maintenanceForm, cost: e.target.value })} />
            <input placeholder="Notes" value={maintenanceForm.notes} onChange={e => setMaintenanceForm({ ...maintenanceForm, notes: e.target.value })} />
            <button>Add Maintenance</button>
          </form>
        </>
      )}

      <h3>{canManage ? '6.' : '1.'} Asset Register</h3>
      <DataTable columns={[
        { key: 'asset_code', label: 'Code' },
        { key: 'name', label: 'Asset' },
        { key: 'asset_type', label: 'Type' },
        { key: 'category_name', label: 'Category' },
        { key: 'brand', label: 'Brand' },
        { key: 'model', label: 'Model' },
        { key: 'serial_number', label: 'Serial No.' },
        { key: 'status', label: 'Status' },
        { key: 'assigned_to_name', label: 'Assigned To' },
        { key: 'warranty_end_date', label: 'Warranty End' },
        { key: 'actions', label: 'Actions', render: row => canManage ? (
          <div className="actions">
            {row.status === 'ASSIGNED' && <button onClick={() => returnAsset(row)}>Return</button>}
            {row.status !== 'ASSIGNED' && <button onClick={() => changeStatus(row, 'mark-available')}>Available</button>}
            {row.status !== 'ASSIGNED' && <button onClick={() => changeStatus(row, 'mark-maintenance')}>Maintenance</button>}
            <button onClick={() => changeStatus(row, 'mark-damaged')}>Damaged</button>
            <button className="dangerBtn" onClick={() => changeStatus(row, 'mark-lost')}>Lost</button>
            <button className="dangerBtn" onClick={() => changeStatus(row, 'mark-retired')}>Retire</button>
          </div>
        ) : '-' }
      ]} rows={assets} />

      <h3>{canManage ? '7.' : '2.'} Assignment History</h3>
      <DataTable columns={[
        { key: 'asset_code', label: 'Asset Code' },
        { key: 'asset_name', label: 'Asset' },
        { key: 'employee_name', label: 'Employee' },
        { key: 'status', label: 'Status' },
        { key: 'assigned_at', label: 'Assigned At' },
        { key: 'returned_at', label: 'Returned At' },
        { key: 'expected_return_date', label: 'Expected Return' }
      ]} rows={assignments} />

      <h3>{canManage ? '8.' : '3.'} Asset Documents</h3>
      <DataTable columns={[
        { key: 'asset_code', label: 'Asset Code' },
        { key: 'asset_name', label: 'Asset' },
        { key: 'title', label: 'Title' },
        { key: 'category', label: 'Category' },
        { key: 'file_name', label: 'File' },
        { key: 'size', label: 'Size' },
        { key: 'actions', label: 'Actions', render: row => <button onClick={() => downloadDocument(row)}>Download</button> }
      ]} rows={documents} />

      <h3>{canManage ? '9.' : '4.'} Maintenance</h3>
      <DataTable columns={[
        { key: 'asset_code', label: 'Asset Code' },
        { key: 'asset_name', label: 'Asset' },
        { key: 'maintenance_type', label: 'Type' },
        { key: 'status', label: 'Status' },
        { key: 'start_date', label: 'Start' },
        { key: 'end_date', label: 'End' },
        { key: 'vendor', label: 'Vendor' },
        { key: 'cost', label: 'Cost' }
      ]} rows={maintenance} />
    </section>
  )
}
