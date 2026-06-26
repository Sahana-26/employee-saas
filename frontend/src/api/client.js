import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh')
      if (refresh) {
        const res = await axios.post(`${api.defaults.baseURL}/auth/token/refresh/`, { refresh })
        localStorage.setItem('access', res.data.access)
        original.headers.Authorization = `Bearer ${res.data.access}`
        return api(original)
      }
    }
    return Promise.reject(error)
  }
)

export default api
