import React from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { hasRole } from '../utils/roles.js'

export default function RoleRoute({ roles }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="center">Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  if (!hasRole(user, roles)) return <Navigate to="/" replace />
  return <Outlet />
}
