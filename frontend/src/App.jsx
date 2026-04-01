import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import ResetPassword from './pages/ResetPassword'
import Dashboard from './pages/Dashboard'
import Kanban from './pages/Kanban'
import InterviewPrep from './pages/InterviewPrep'
import Analytics from './pages/Analytics'
import Layout from './components/Layout'
import { AuthProvider, useAuth } from './context/AuthContext'

const BACKEND_URL = import.meta.env.VITE_API_URL || 'https://placewise-api.onrender.com'

// Keeps the Render free-tier backend warm so the first API call after idle
// doesn't hit a cold-start 503 (which has no CORS headers, causing a misleading
// "CORS error" in DevTools). Pings every 13 minutes — just under Render's 15-min
// spin-down threshold.
function useBackendKeepAlive() {
  useEffect(() => {
    const ping = () => fetch(`${BACKEND_URL}/`, { method: 'GET' }).catch(() => {})
    ping() // immediate ping on app load
    const id = setInterval(ping, 13 * 60 * 1000)
    return () => clearInterval(id)
  }, [])
}

function PrivateRoute({ children }) {
  const { token } = useAuth()
  return token ? children : <Navigate to="/login" />
}

export default function App() {
  useBackendKeepAlive()

  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route index element={<Navigate to="/dashboard" />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="kanban" element={<Kanban />} />
            <Route path="interview" element={<InterviewPrep />} />
            <Route path="analytics" element={<Analytics />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}