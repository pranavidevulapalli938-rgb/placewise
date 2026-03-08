import { useState, useEffect, useRef } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth, API } from '../context/AuthContext'
import {
  LayoutDashboard, Kanban, MessageSquare, BarChart3,
  LogOut, Menu, X, ChevronDown
} from 'lucide-react'

const NAV = [
  { to: '/dashboard',  label: 'Dashboard',     icon: LayoutDashboard },
  { to: '/kanban',     label: 'Kanban',         icon: Kanban          },
  { to: '/interview',  label: 'Interview Prep', icon: MessageSquare   },
  { to: '/analytics',  label: 'Analytics',      icon: BarChart3       },
]

export default function Layout() {
  const { logout } = useAuth()
  const navigate   = useNavigate()
  const [open,    setOpen]    = useState(false)   // mobile menu
  const [dropOpen, setDropOpen] = useState(false) // avatar dropdown
  const [userEmail, setUserEmail] = useState('')
  const dropRef = useRef(null)

  // Fetch current user email for avatar initial
  useEffect(() => {
    API.get('/me')
      .then(r => setUserEmail(r.data.email || ''))
      .catch(() => {})
  }, [])

  // Close dropdown on outside click
  useEffect(() => {
    function handler(e) {
      if (dropRef.current && !dropRef.current.contains(e.target)) {
        setDropOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const initial  = userEmail ? userEmail[0].toUpperCase() : '?'
  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="min-h-screen bg-[#0f1117] text-white flex flex-col">

      {/* ── Top Nav ── */}
      <header className="sticky top-0 z-40 bg-[#0f1117]/80 backdrop-blur border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between gap-4">

          {/* Logo */}
          <span className="text-white font-bold text-lg tracking-tight select-none">
            Place<span className="text-violet-400">Wise</span>
          </span>

          {/* Desktop nav links */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-violet-500/15 text-violet-400'
                      : 'text-white/50 hover:text-white hover:bg-white/5'
                  }`
                }
              >
                <Icon size={15} />
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Avatar + dropdown */}
          <div className="flex items-center gap-2">
            <div className="relative" ref={dropRef}>
              <button
                onClick={() => setDropOpen(v => !v)}
                className="flex items-center gap-1.5 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-violet-500/40 rounded-xl px-2.5 py-1.5 transition-all"
              >
                {/* Avatar circle with email initial */}
                <div className="w-7 h-7 rounded-lg bg-violet-600 flex items-center justify-center text-white text-xs font-bold select-none">
                  {initial}
                </div>
                {userEmail && (
                  <span className="hidden sm:block text-white/70 text-sm max-w-[140px] truncate">
                    {userEmail}
                  </span>
                )}
                <ChevronDown size={13} className="text-white/40" />
              </button>

              {dropOpen && (
                <div className="absolute right-0 mt-2 w-52 bg-[#1a1d2e] border border-white/10 rounded-xl shadow-xl py-1.5 z-50">
                  <div className="px-3.5 py-2 border-b border-white/[0.06]">
                    <p className="text-white/40 text-xs">Signed in as</p>
                    <p className="text-white/80 text-sm font-medium truncate">{userEmail}</p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-red-400 hover:bg-red-500/10 transition-colors mt-0.5"
                  >
                    <LogOut size={14} />
                    Sign out
                  </button>
                </div>
              )}
            </div>

            {/* Mobile menu toggle */}
            <button
              className="md:hidden p-2 rounded-lg text-white/50 hover:text-white hover:bg-white/5 transition-colors"
              onClick={() => setOpen(v => !v)}
            >
              {open ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>

        {/* Mobile nav */}
        {open && (
          <div className="md:hidden border-t border-white/[0.06] px-4 pb-3 pt-2 flex flex-col gap-1">
            {NAV.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-violet-500/15 text-violet-400'
                      : 'text-white/50 hover:text-white hover:bg-white/5'
                  }`
                }
              >
                <Icon size={15} />
                {label}
              </NavLink>
            ))}
          </div>
        )}
      </header>

      {/* ── Page content ── */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}