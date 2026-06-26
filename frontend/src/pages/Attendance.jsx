import React, { useEffect, useState } from 'react'
import api from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'

function minutesToHours(minutes) {
  if (!minutes) return '0h'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${h}h ${m}m`
}

export default function Attendance() {
  const [rows, setRows] = useState([])
  const [myShift, setMyShift] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const load = async () => {
    const [attendanceRes, shiftRes] = await Promise.all([
      api.get('/attendance/'),
      api.get('/attendance/my-shift/')
    ])
    setRows(attendanceRes.data.results || attendanceRes.data)
    setMyShift(shiftRes.data)
  }

  useEffect(() => { load().catch(() => {}) }, [])

  const checkIn = async () => {
    setMessage('')
    setError('')
    try {
      await api.post('/attendance/check-in/')
      setMessage('Checked in successfully.')
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to check in'))
    }
  }

  const checkOut = async () => {
    setMessage('')
    setError('')
    try {
      await api.post('/attendance/check-out/')
      setMessage('Checked out successfully.')
      load()
    } catch (err) {
      setError(JSON.stringify(err.response?.data || 'Unable to check out'))
    }
  }

  return (
    <section>
      <PageHeader title="Attendance" subtitle="Track check-in, check-out, shift, late marks, holidays, weekly offs, and overtime." action={<div className="actions"><button onClick={checkIn}>Check In</button><button onClick={checkOut}>Check Out</button></div>} />
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      {myShift && (
        <div className="infoCard">
          <strong>Today:</strong> {myShift.date} &nbsp; | &nbsp;
          <strong>Shift:</strong> {myShift.shift ? `${myShift.shift.name} (${myShift.shift.start_time} - ${myShift.shift.end_time})` : 'No shift assigned'} &nbsp; | &nbsp;
          <strong>Holiday:</strong> {myShift.holiday ? myShift.holiday.name : 'No'}
        </div>
      )}
      <DataTable columns={[
        { key: 'employee_name', label: 'Employee' },
        { key: 'date', label: 'Date' },
        { key: 'shift_name', label: 'Shift' },
        { key: 'holiday_name', label: 'Holiday' },
        { key: 'check_in', label: 'Check In' },
        { key: 'check_out', label: 'Check Out' },
        { key: 'status', label: 'Status' },
        { key: 'work_mode', label: 'Mode' },
        { key: 'duration_minutes', label: 'Worked', render: row => minutesToHours(row.duration_minutes) },
        { key: 'late_minutes', label: 'Late', render: row => `${row.late_minutes || 0} min` },
        { key: 'overtime_minutes', label: 'OT', render: row => `${row.overtime_minutes || 0} min` }
      ]} rows={rows} />
    </section>
  )
}
