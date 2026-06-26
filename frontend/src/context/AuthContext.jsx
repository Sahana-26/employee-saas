import React, { createContext, useContext, useEffect, useState } from 'react'
import api from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadMe = async () => {
    const token = localStorage.getItem('access')
    if (!token) {
      setLoading(false)
      return
    }
    try {
      const res = await api.get('/auth/me/')
      setUser(res.data)
    } catch {
      localStorage.removeItem('access')
      localStorage.removeItem('refresh')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMe()
  }, [])

  const login = async (email, password) => {
    const res = await api.post('/auth/token/', { email, password })
    localStorage.setItem('access', res.data.access)
    localStorage.setItem('refresh', res.data.refresh)
    setUser(res.data.user)
  }

  const logout = () => {
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, login, logout, setUser }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
