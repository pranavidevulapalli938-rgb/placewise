import { useState } from 'react'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import { useAuth, API } from '../context/AuthContext'
import { GraduationCap, Mail, Lock, ArrowRight, Loader2, KeyRound, CheckCircle2 } from 'lucide-react'

// ── Forgot Password Modal ────────────────────────────────────────────────────
function ForgotPasswordModal({ onClose }) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!email) return
    setLoading(true)
    setError('')
    try {
      await API.post('/auth/forgot-password', { email })
      setSent(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-[#13151f] border border-white/10 rounded-2xl w-full max-w-md shadow-2xl p-8">
        <div className="flex flex-col items-center mb-6">
          <div className="w-12 h-12 rounded-2xl bg-violet-500/20 flex items-center justify-center mb-3">
            <KeyRound size={22} className="text-violet-400" />
          </div>
          <h2 className="text-lg font-bold text-white">Reset your password</h2>
          <p className="text-white/40 text-sm mt-1 text-center">
            Enter your registered email — we'll send a reset link if the account exists.
          </p>
        </div>

        {sent ? (
          <div className="flex flex-col items-center gap-4 py-4">
            <CheckCircle2 size={40} className="text-emerald-400" />
            <p className="text-emerald-400 font-medium text-center">
              Reset link sent! Check your inbox (and spam folder).
            </p>
            <button
              onClick={onClose}
              className="w-full bg-white/5 hover:bg-white/10 text-white py-3 rounded-xl text-sm font-medium transition-all mt-2"
            >
              Close
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm px-4 py-3 rounded-xl">
                {error}
              </div>
            )}
            <div className="relative">
              <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                placeholder="you@university.edu"
                className="w-full bg-white/5 border border-white/10 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 focus:bg-violet-500/5 transition-all"
              />
            </div>
            <button
              onClick={handleSubmit}
              disabled={loading || !email}
              className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : 'Send Reset Link'}
            </button>
            <button
              onClick={onClose}
              className="w-full text-white/30 hover:text-white py-2 text-sm transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Login Page ───────────────────────────────────────────────────────────────
export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [rememberMe, setRememberMe] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showForgot, setShowForgot] = useState(false)

  const registered = location.state?.registered
  const resetSent   = location.state?.resetSent

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(form.email, form.password, rememberMe)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0f1117] flex items-center justify-center p-4 font-['Sora',sans-serif]">
      {showForgot && <ForgotPasswordModal onClose={() => setShowForgot(false)} />}

      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-violet-600/10 rounded-full blur-[120px]" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-10">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-2xl shadow-violet-500/40 mb-4">
            <GraduationCap size={26} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Welcome back</h1>
          <p className="text-white/40 text-sm mt-1">Sign in to PlaceWise</p>
        </div>

        <div className="bg-[#13151f] border border-white/8 rounded-2xl p-8 shadow-2xl">
          {registered && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm px-4 py-3 rounded-xl mb-5">
              ✅ Account created! Please sign in.
            </div>
          )}
          {resetSent && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm px-4 py-3 rounded-xl mb-5">
              ✅ Password reset link sent — check your inbox.
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm px-4 py-3 rounded-xl">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <label className="text-xs font-medium text-white/50 uppercase tracking-wider">Email</label>
              <div className="relative">
                <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={e => setForm({ ...form, email: e.target.value })}
                  placeholder="you@university.edu"
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 focus:bg-violet-500/5 transition-all"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium text-white/50 uppercase tracking-wider">Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                <input
                  type="password"
                  required
                  value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })}
                  placeholder="Your password"
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 focus:bg-violet-500/5 transition-all"
                />
              </div>
            </div>

            {/* Remember Me + Forgot Password */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2.5 cursor-pointer group">
                <div
                  onClick={() => setRememberMe(!rememberMe)}
                  className={`w-4 h-4 rounded border flex items-center justify-center transition-all cursor-pointer ${
                    rememberMe
                      ? 'bg-violet-600 border-violet-600'
                      : 'border-white/20 bg-white/5 group-hover:border-violet-500/50'
                  }`}
                >
                  {rememberMe && (
                    <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                      <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                </div>
                <span className="text-sm text-white/50 group-hover:text-white/70 transition-colors">Remember me</span>
              </label>
              <button
                type="button"
                onClick={() => setShowForgot(true)}
                className="text-sm text-violet-400 hover:text-violet-300 transition-colors"
              >
                Forgot password?
              </button>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold py-3 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-violet-500/25 disabled:opacity-50 mt-2"
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : <>Sign In <ArrowRight size={16} /></>}
            </button>
          </form>

          <p className="text-center text-sm text-white/30 mt-6">
            Don't have an account?{' '}
            <Link to="/register" className="text-violet-400 hover:text-violet-300 font-medium">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}