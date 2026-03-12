import { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const API = axios.create({ baseURL: BASE_URL })
export const AI_API = axios.create({ baseURL: import.meta.env.VITE_AI_URL || 'http://localhost:3001' })

// Attach JWT token to every request automatically
API.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// FIX: also attach token to AI_API requests (needed for Node.js auth middleware)
AI_API.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(
    () => localStorage.getItem('token') || sessionStorage.getItem('token') || null
  )
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const savedToken = localStorage.getItem('token') || sessionStorage.getItem('token')
    if (savedToken) {
      API.get('/me')
        .then(r => {
          setUser(r.data)
          setToken(savedToken)
        })
        .catch(() => {
          localStorage.removeItem('token')
          sessionStorage.removeItem('token')
          setToken(null)
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
    setToken(access_token)
    const me = await API.get('/me')
    setUser(me.data)
    return r.data
  }

  // FIX: add register function that was missing (Register.jsx calls useAuth().register)
  const register = async (email, password) => {
    const r = await API.post('/register', { email, password })
    return r.data
  }

  const logout = () => {
    localStorage.removeItem('token')
    sessionStorage.removeItem('token')
    setUser(null)
    setToken(null)
  }

  return (
    // FIX: expose token and register in context value
    <AuthContext.Provider value={{ user, token, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}