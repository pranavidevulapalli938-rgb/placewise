import { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

// ── Single source of truth for the API base URL ───────────────────────────────
// In development:  reads from frontend/.env.development  → http://localhost:8000
// In production:   reads from frontend/.env.production   → https://your-app.onrender.com
// Vercel automatically uses .env.production when building.
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const API = axios.create({ baseURL: BASE_URL })

// Attach JWT token to every request automatically
API.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Restore session on page reload
    const token = localStorage.getItem('token') || sessionStorage.getItem('token')
    if (token) {
      API.get('/me')
        .then(r => setUser(r.data))
        .catch(() => {
          localStorage.removeItem('token')
          sessionStorage.removeItem('token')
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (email, password, rememberMe = false) => {
    const r = await API.post('/auth/login', { email, password })
    const { access_token } = r.data
    if (rememberMe) {
      localStorage.setItem('token', access_token)
    } else {
      sessionStorage.setItem('token', access_token)
    }
    const me = await API.get('/me')
    setUser(me.data)
    return r.data
  }

  const logout = () => {
    localStorage.removeItem('token')
    sessionStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}