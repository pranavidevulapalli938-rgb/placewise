import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { API } from '../context/AuthContext'
import { GraduationCap, Lock, ArrowRight, Loader2, CheckCircle2, XCircle } from 'lucide-react'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [form, setForm] = useState({ password: '', confirm: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [tokenValid, setTokenValid] = useState(null) // null = checking, true/false

  // Verify token on mount
  useEffect(() => {
    if (!token) { setTokenValid(false); return }
    API.get(`/auth/verify-reset-token?token=${token}`)
      .then(() => setTokenValid(true))
      .catch(() => setTokenValid(false))
  }, [token])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password !== form.confirm) return setError('Passwords do not match')
    if (form.password.length < 8) return setError('Password must be at least 8 characters')
    setLoading(true)
    setError('')
    try {
      await API.post('/auth/reset-password', { token, new_password: form.password })
      setSuccess(true)
      setTimeout(() => navigate('/login', { state: { resetSent: false } }), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Reset failed. The link may have expired.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0f1117] flex items-center justify-center p-4 font-['Sora',sans-serif]">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-violet-600/10 rounded-full blur-[120px]" />
      </div>

      <div className="relative w-full max-w-md">
        <div className="flex flex-col items-center mb-10">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-2xl shadow-violet-500/40 mb-4">
            <GraduationCap size={26} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Set new password</h1>
          <p className="text-white/40 text-sm mt-1">PlaceWise — Password Reset</p>
        </div>

        <div className="bg-[#13151f] border border-white/8 rounded-2xl p-8 shadow-2xl">
          {/* Token checking */}
          {tokenValid === null && (
            <div className="flex justify-center py-8">
              <Loader2 size={24} className="animate-spin text-violet-400" />
            </div>
          )}

          {/* Invalid token */}
          {tokenValid === false && (
            <div className="flex flex-col items-center gap-4 py-4">
              <XCircle size={40} className="text-red-400" />
              <p className="text-red-400 font-medium text-center">
                This reset link is invalid or has expired.
              </p>
              <p className="text-white/30 text-sm text-center">
                Reset links expire after 30 minutes. Please request a new one.
              </p>
              <Link
                to="/login"
                className="w-full text-center bg-violet-600 hover:bg-violet-500 text-white py-3 rounded-xl text-sm font-semibold transition-all"
              >
                Back to Login
              </Link>
            </div>
          )}

          {/* Success */}
          {success && (
            <div className="flex flex-col items-center gap-4 py-4">
              <CheckCircle2 size={40} className="text-emerald-400" />
              <p className="text-emerald-400 font-medium text-center">
                Password reset successfully!
              </p>
              <p className="text-white/30 text-sm text-center">
                Redirecting you to login...
              </p>
            </div>
          )}

          {/* Reset form */}
          {tokenValid === true && !success && (
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm px-4 py-3 rounded-xl">
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-xs font-medium text-white/50 uppercase tracking-wider">New Password</label>
                <div className="relative">
                  <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                  <input
                    type="password"
                    required
                    value={form.password}
                    onChange={e => setForm({ ...form, password: e.target.value })}
                    placeholder="Min. 8 characters"
                    className="w-full bg-white/5 border border-white/10 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 focus:bg-violet-500/5 transition-all"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium text-white/50 uppercase tracking-wider">Confirm Password</label>
                <div className="relative">
                  <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                  {form.confirm && form.confirm === form.password && (
                    <CheckCircle2 size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-emerald-400" />
                  )}
                  <input
                    type="password"
                    required
                    value={form.confirm}
                    onChange={e => setForm({ ...form, confirm: e.target.value })}
                    placeholder="Re-enter password"
                    className="w-full bg-white/5 border border-white/10 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 focus:bg-violet-500/5 transition-all"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-violet-500/25 disabled:opacity-50"
              >
                {loading ? <Loader2 size={18} className="animate-spin" /> : <>Reset Password <ArrowRight size={16} /></>}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}