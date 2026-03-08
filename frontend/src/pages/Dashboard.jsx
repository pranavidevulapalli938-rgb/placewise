import { useEffect, useState } from 'react'
import { API } from '../context/AuthContext'
import {
  Plus, Briefcase, TrendingUp, CheckCircle2,
  XCircle, Mail, Loader2, Trash2, RefreshCw,
  Building2, ChevronDown, StickyNote, X,
  Puzzle, Download, AlertTriangle, ChevronRight, ExternalLink
} from 'lucide-react'

const STATUS_COLORS = {
  'Applied':              'bg-blue-500/15 text-blue-400 border-blue-500/20',
  'OA Received':          'bg-amber-500/15 text-amber-400 border-amber-500/20',
  'Interview Scheduled':  'bg-violet-500/15 text-violet-400 border-violet-500/20',
  'Selected':             'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  'Rejected':             'bg-red-500/15 text-red-400 border-red-500/20',
}

const STATUSES = ['Applied', 'OA Received', 'Interview Scheduled', 'Selected', 'Rejected']

// ── Extension Banner ─────────────────────────────────────────────────────────
// Detects if the Chrome extension is installed by listening for a custom event
// that content.js would fire, or falls back to showing the banner.
function ExtensionBanner() {
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem('ext_banner_dismissed') === 'true'
  )
  const [installed, setInstalled] = useState(false)

  useEffect(() => {
    // Chrome extensions can expose themselves via window.postMessage or
    // a custom DOM event. We attempt to detect via chrome.runtime if available.
    try {
      // If the content script is injected on this page, it won't be.
      // Instead we check sessionStorage flag that the extension can set.
      const extFlag = sessionStorage.getItem('placewise_ext_installed')
      if (extFlag === 'true') { setInstalled(true); return }
    } catch {}
    // Default: assume not installed and show the banner
    setInstalled(false)
  }, [])

  if (installed || dismissed) return null

  const handleDismiss = () => {
    localStorage.setItem('ext_banner_dismissed', 'true')
    setDismissed(true)
  }

  const handleDownload = () => {
    // Downloads the extension zip from your public folder.
    // Place your zipped extension at: frontend/public/placewise-extension.zip
    const link = document.createElement('a')
    link.href = '/placewise-extension.zip'
    link.download = 'placewise-extension.zip'
    link.click()
  }

  return (
    <div className="relative bg-gradient-to-r from-violet-500/10 to-indigo-500/10 border border-violet-500/20 rounded-2xl p-5 flex items-center gap-4 overflow-hidden">
      {/* Glow blob */}
      <div className="absolute -right-10 -top-10 w-40 h-40 bg-violet-600/10 rounded-full blur-2xl pointer-events-none" />

      {/* Icon */}
      <div className="w-11 h-11 rounded-xl bg-violet-500/20 flex items-center justify-center flex-shrink-0">
        <Puzzle size={20} className="text-violet-400" />
      </div>

      {/* Text */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white">
          Save jobs in one click — Install the PlaceWise Extension
        </p>
        <p className="text-xs text-white/40 mt-0.5">
          Browse Naukri, LinkedIn, Internshala, Indeed, or Wellfound and save jobs directly to your tracker.
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={handleDownload}
          className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 text-white px-4 py-2 rounded-xl text-sm font-semibold transition-all shadow-lg shadow-violet-500/20"
        >
          <Download size={14} />
          Download
        </button>
        <button
          onClick={handleDismiss}
          className="text-white/20 hover:text-white/60 transition-colors p-1"
          title="Dismiss"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  )
}

// Extension Install Instructions Modal
function ExtensionHelpModal({ onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-[#13151f] border border-white/10 rounded-2xl w-full max-w-lg shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-violet-500/20 flex items-center justify-center">
              <Puzzle size={16} className="text-violet-400" />
            </div>
            <div>
              <h3 className="font-semibold text-white text-sm">How to install the extension</h3>
              <p className="text-xs text-white/40 mt-0.5">One-time setup, takes 30 seconds</p>
            </div>
          </div>
          <button onClick={onClose} className="text-white/30 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {[
            { step: '1', text: 'Click "Download Extension" and save the zip file' },
            { step: '2', text: 'Unzip the downloaded file to a folder on your computer' },
            { step: '3', text: 'Open Chrome and go to chrome://extensions' },
            { step: '4', text: 'Enable "Developer mode" (toggle, top-right corner)' },
            { step: '5', text: 'Click "Load unpacked" and select the unzipped folder' },
            { step: '6', text: 'The PlaceWise icon will appear in your Chrome toolbar!' },
          ].map(({ step, text }) => (
            <div key={step} className="flex items-start gap-4">
              <div className="w-6 h-6 rounded-full bg-violet-500/20 text-violet-400 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                {step}
              </div>
              <p className="text-sm text-white/70">{text}</p>
            </div>
          ))}

          <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-start gap-3 mt-2">
            <AlertTriangle size={16} className="text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-400/80">
              Make sure the PlaceWise backend is running at <span className="font-mono">localhost:8000</span> before using the extension.
            </p>
          </div>
        </div>

        <div className="p-6 border-t border-white/5">
          <button
            onClick={() => {
              const link = document.createElement('a')
              link.href = '/placewise-extension.zip'
              link.download = 'placewise-extension.zip'
              link.click()
            }}
            className="w-full flex items-center justify-center gap-2 bg-violet-600 hover:bg-violet-500 text-white py-3 rounded-xl text-sm font-semibold transition-all"
          >
            <Download size={16} />
            Download Extension (.zip)
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Stat Card ────────────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5 flex items-center gap-4">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value}</p>
        <p className="text-xs text-white/40 mt-0.5">{label}</p>
      </div>
    </div>
  )
}

// ── Note Modal ───────────────────────────────────────────────────────────────
function NoteModal({ app, onClose }) {
  const [notes, setNotes] = useState([])
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    API.get(`/applications/${app.id}/notes`)
      .then(r => setNotes(r.data))
      .catch(() => setNotes([]))
      .finally(() => setLoading(false))
  }, [app.id])

  const addNote = async () => {
    if (!text.trim()) return
    try {
      await API.post(`/applications/${app.id}/notes`, { text })
      const r = await API.get(`/applications/${app.id}/notes`)
      setNotes(r.data)
      setText('')
    } catch {}
  }

  const deleteNote = async (nid) => {
    try {
      await API.delete(`/applications/${app.id}/notes/${nid}`)
      setNotes(notes.filter(n => n.id !== nid))
    } catch {}
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-[#13151f] border border-white/10 rounded-2xl w-full max-w-lg shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <div>
            <h3 className="font-semibold text-white">{app.company}</h3>
            <p className="text-xs text-white/40 mt-0.5">{app.role}</p>
          </div>
          <button onClick={onClose} className="text-white/30 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>
        <div className="p-6 space-y-4 max-h-72 overflow-y-auto">
          {loading
            ? <Loader2 size={18} className="animate-spin text-white/30 mx-auto" />
            : notes.length === 0
              ? <p className="text-white/30 text-sm text-center">No notes yet</p>
              : notes.map(n => (
                <div key={n.id} className="flex items-start gap-3 bg-white/3 rounded-xl p-3">
                  <p className="flex-1 text-sm text-white/70">{n.text}</p>
                  <button onClick={() => deleteNote(n.id)} className="text-white/20 hover:text-red-400 transition-colors mt-0.5">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
          }
        </div>
        <div className="p-6 border-t border-white/5 flex gap-3">
          <input
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addNote()}
            placeholder="Add a note..."
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 transition-all"
          />
          <button onClick={addNote} className="bg-violet-600 hover:bg-violet-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors">
            Add
          </button>
        </div>
      </div>
    </div>
  )
}

// ── API Error Banner ─────────────────────────────────────────────────────────
function ApiErrorBanner({ error, onRetry }) {
  return (
    <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-5 flex items-start gap-4">
      <AlertTriangle size={20} className="text-red-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm font-semibold text-red-400">Cannot connect to backend</p>
        <p className="text-xs text-white/40 mt-1">{error}</p>
        <p className="text-xs text-white/30 mt-1">
          Make sure FastAPI is running: <span className="font-mono text-white/50">uvicorn main:app --reload --port 8000</span>
        </p>
      </div>
      <button
        onClick={onRetry}
        className="flex items-center gap-1.5 bg-red-500/15 hover:bg-red-500/25 text-red-400 px-3 py-2 rounded-xl text-xs font-medium transition-all flex-shrink-0"
      >
        <RefreshCw size={13} /> Retry
      </button>
    </div>
  )
}

// ── Dashboard ────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState(null)   // ← NEW: tracks fetch errors
  const [adding, setAdding] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [form, setForm] = useState({ company: '', role: '', source_url: '' })
  const [msg, setMsg] = useState('')
  const [noteApp, setNoteApp] = useState(null)
  const [gmailConnected, setGmailConnected] = useState(false)
  const [showExtHelp, setShowExtHelp] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')

  // ── FIX: wrapped in try/catch so spinner never gets stuck ──────────────────
  const fetchApps = async () => {
    setApiError(null)
    
    try {
      const r = await API.get('/applications')
      setApps(r.data)
    } catch (err) {
      const msg = err?.response?.status === 401
        ? 'Session expired — please log out and log back in.'
        : err?.message?.includes('Network')
          ? 'Network error — is the backend running on port 8000?'
          : `Error ${err?.response?.status || ''}: ${err?.response?.data?.detail || err?.message}`
      setApiError(msg)
      setApps([])
    } finally {
      setLoading(false)  // ← always runs now
    }
  }

  const fetchGmailStatus = async () => {
    try {
      const r = await API.get('/gmail/status')
      setGmailConnected(r.data.gmail_connected)
    } catch {}
  }

  useEffect(() => { fetchApps(); fetchGmailStatus() }, [])

  const addApp = async (e) => {
    e.preventDefault()
    if (!form.company || !form.role) return
    try {
      await API.post('/applications', form)
      setForm({ company: '', role: '', source_url: '' })
      setAdding(false)
      fetchApps()
    } catch {}
  }

  const updateStatus = async (id, status) => {
    try {
      await API.patch(`/applications/${id}/status`, { status })
      fetchApps()
    } catch {}
  }

  const deleteApp = async (id) => {
    try {
      await API.delete(`/applications/${id}`)
      fetchApps()
    } catch {}
  }

  const connectGmail = async () => {
    try {
      const r = await API.get('/gmail/connect')
      window.open(r.data.auth_url, '_blank')
    } catch {}
  }

  const syncGmail = async () => {
    setSyncing(true)
    try {
      const r = await API.post('/gmail/sync')
      setMsg(`✅ Synced! ${r.data.created} new, ${r.data.updated} updated`)
      fetchApps()
    } catch {
      setMsg('❌ Gmail sync failed')
    } finally {
      setSyncing(false)
      setTimeout(() => setMsg(''), 4000)
    }
  }

  const stats = {
    total:    apps.length,
    active:   apps.filter(a => !['Selected', 'Rejected'].includes(a.status)).length,
    selected: apps.filter(a => a.status === 'Selected').length,
    rejected: apps.filter(a => a.status === 'Rejected').length,
  }
  const filteredApps = apps.filter(a => {
    const matchSearch = search === '' ||
      a.company.toLowerCase().includes(search.toLowerCase()) ||
      (a.role || '').toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'All' || a.status === statusFilter
    return matchSearch && matchStatus
  })

  return (
    <div className="space-y-6 font-['Sora',sans-serif]">
      {noteApp && <NoteModal app={noteApp} onClose={() => setNoteApp(null)} />}
      {showExtHelp && <ExtensionHelpModal onClose={() => setShowExtHelp(false)} />}

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Dashboard</h1>
          <p className="text-white/40 text-sm mt-0.5">Track all your placement applications</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Extension quick-access button */}
          <button
            onClick={() => setShowExtHelp(true)}
            className="flex items-center gap-2 bg-[#13151f] border border-white/10 hover:border-violet-500/40 text-white/50 hover:text-violet-400 px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
            title="Install browser extension"
          >
            <Puzzle size={16} /> Extension
          </button>

          {!gmailConnected ? (
            <button
              onClick={connectGmail}
              className="flex items-center gap-2 bg-[#13151f] border border-white/10 hover:border-violet-500/40 text-white/60 hover:text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
            >
              <Mail size={16} /> Connect Gmail
            </button>
          ) : (
            <button
              onClick={syncGmail}
              disabled={syncing}
              className="flex items-center gap-2 bg-[#13151f] border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
            >
              <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
              {syncing ? 'Syncing...' : 'Sync Gmail'}
            </button>
          )}

          <button
            onClick={() => setAdding(true)}
            className="flex items-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-semibold shadow-lg shadow-violet-500/20 transition-all"
          >
            <Plus size={16} /> Add Application
          </button>
        </div>
      </div>

      {/* Extension install banner (dismissable) */}
      <ExtensionBanner />

      {/* API error banner */}
      {apiError && <ApiErrorBanner error={apiError} onRetry={fetchApps} />}

      {/* Gmail sync message */}
      {msg && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm px-4 py-3 rounded-xl">
          {msg}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Briefcase}    label="Total Applied"  value={stats.total}    color="bg-blue-500/15 text-blue-400" />
        <StatCard icon={TrendingUp}   label="Active"         value={stats.active}   color="bg-violet-500/15 text-violet-400" />
        <StatCard icon={CheckCircle2} label="Selected"       value={stats.selected} color="bg-emerald-500/15 text-emerald-400" />
        <StatCard icon={XCircle}      label="Rejected"       value={stats.rejected} color="bg-red-500/15 text-red-400" />
      </div>

      {/* Add Application Form */}
      {adding && (
        <div className="bg-[#13151f] border border-violet-500/20 rounded-2xl p-6">
          <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Plus size={18} className="text-violet-400" /> New Application
          </h3>
          <form onSubmit={addApp} className="flex gap-3 flex-wrap">
            <input
              value={form.company}
              onChange={e => setForm({ ...form, company: e.target.value })}
              placeholder="Company name"
              required
              className="flex-1 min-w-40 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 transition-all"
            />
            <input
              value={form.role}
              onChange={e => setForm({ ...form, role: e.target.value })}
              placeholder="Role / Position"
              required
              className="flex-1 min-w-40 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 transition-all"
            />
            <input
              value={form.source_url}
              onChange={e => setForm({ ...form, source_url: e.target.value })}
              placeholder="Job URL (optional)"
              type="url"
              className="flex-1 min-w-40 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 transition-all"
            />
            <button type="submit" className="bg-violet-600 hover:bg-violet-500 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors">
              Save
            </button>
            <button type="button" onClick={() => setAdding(false)} className="text-white/30 hover:text-white px-4 py-2.5 rounded-xl text-sm transition-colors">
              Cancel
            </button>
          </form>
        </div>
      )}

      {/* Applications Table */}
      <div className="bg-[#13151f] border border-white/5 rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Building2 size={18} className="text-white/40" /> Applications
            </h2>
            <span className="text-xs text-white/30">{filteredApps.length} of {apps.length} total</span>
          </div>
          <div className="flex gap-2 flex-wrap">
            <input
              type="text"
              placeholder="Search company or role..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="flex-1 min-w-[180px] bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-violet-500/50"
            />
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white/70 focus:outline-none focus:border-violet-500/50"
            >
              {['All', 'Applied', 'OA Received', 'Interview Scheduled', 'Selected', 'Rejected'].map(s => (
                <option key={s} value={s} className="bg-[#13151f]">{s}</option>
              ))}
            </select>
          </div>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Loader2 size={24} className="animate-spin text-violet-400" />
            <p className="text-white/30 text-xs">Connecting to backend...</p>
          </div>
        ) : apiError ? (
          // Show empty state (error already shown above)
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <AlertTriangle size={36} className="text-red-400/30" />
            <p className="text-white/30 text-sm">Could not load applications</p>
            <button onClick={fetchApps} className="text-violet-400 text-sm hover:underline flex items-center gap-1">
              <RefreshCw size={12} /> Try again
            </button>
          </div>
        ) : filteredApps.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Briefcase size={36} className="text-white/10" />
            <p className="text-white/30 text-sm">No applications yet</p>
            <button onClick={() => setAdding(true)} className="text-violet-400 text-sm hover:underline flex items-center gap-1">
              <ChevronRight size={14} /> Add your first one
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left border-b border-white/5">
                  <th className="px-6 py-3 text-xs font-medium text-white/30 uppercase tracking-wider">Company</th>
                  <th className="px-6 py-3 text-xs font-medium text-white/30 uppercase tracking-wider">Role</th>
                  <th className="px-6 py-3 text-xs font-medium text-white/30 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-xs font-medium text-white/30 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-3 text-xs font-medium text-white/30 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/3">
                {filteredApps.map(app => (
                  <tr key={app.id} className="hover:bg-white/2 transition-colors group">
                    <td className="px-6 py-4 text-sm font-medium text-white">{app.company}</td>
                    <td className="px-6 py-4 text-sm text-white/60">{app.role}</td>
                    <td className="px-6 py-4">
                      <div className="relative inline-block">
                        <select
                          value={app.status}
                          onChange={e => updateStatus(app.id, e.target.value)}
                          className={`appearance-none pr-7 pl-3 py-1.5 rounded-lg text-xs font-medium border cursor-pointer focus:outline-none ${STATUS_COLORS[app.status] || 'bg-white/10 text-white/60 border-white/10'} bg-transparent`}
                        >
                          {STATUSES.map(s => (
                            <option key={s} value={s} className="bg-[#13151f] text-white">{s}</option>
                          ))}
                        </select>
                        <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none opacity-60" />
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs text-white/30">
                      {app.applied_date ? new Date(app.applied_date).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => setNoteApp(app)}
                          className="text-white/30 hover:text-violet-400 transition-colors"
                          title="Notes"
                        >
                          <StickyNote size={15} />
                        </button>
                        {/* Job posting link (from extension) */}
                        {app.source_url && (
                          <a
                            href={app.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-white/30 hover:text-blue-400 transition-colors"
                            title="Open job posting"
                          >
                            <ExternalLink size={15} />
                          </a>
                        )}
                        {/* Gmail link (for Gmail-synced applications) */}
                        {app.gmail_message_id && (
                          <a
                            href={`https://mail.google.com/mail/u/0/#all/${app.gmail_message_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-white/30 hover:text-violet-400 transition-colors"
                            title="Open in Gmail"
                          >
                            <Mail size={15} />
                          </a>
                        )}
                        <button
                          onClick={() => deleteApp(app.id)}
                          className="text-white/30 hover:text-red-400 transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}