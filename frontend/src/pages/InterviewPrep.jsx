import { useState } from 'react'
import { AI_API } from '../context/AuthContext'
import { Brain, Code2, FileText, Loader2, Send, Star, ChevronRight, RotateCcw } from 'lucide-react'

const TABS = [
  { id: 'hr',        label: 'HR Questions', icon: Brain },
  { id: 'technical', label: 'Coding',       icon: Code2 },
  { id: 'resume',    label: 'Resume',       icon: FileText },
]

// ── HR TAB ──────────────────────────────────────────────
function HRTab() {
  const [questions, setQuestions] = useState([])
  const [current, setCurrent] = useState(null)
  const [answer, setAnswer] = useState('')
  const [evaluation, setEvaluation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [genLoading, setGenLoading] = useState(false)
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('')

  const loadDefault = async () => {
    setGenLoading(true)
    const r = await AI_API.get('/api/hr/questions')
    setQuestions(r.data); setCurrent(r.data[0]); setEvaluation(null); setAnswer('')
    setGenLoading(false)
  }

  const generateCustom = async () => {
    if (!company || !role) return
    setGenLoading(true)
    try {
      const r = await AI_API.post('/api/hr/generate-questions', { company, role })
      setQuestions(r.data.questions); setCurrent(r.data.questions[0]); setEvaluation(null); setAnswer('')
    } finally { setGenLoading(false) }
  }

  const evaluate = async () => {
    if (!answer.trim() || !current) return
    setLoading(true)
    try {
      const r = await AI_API.post('/api/hr/evaluate', { questionId: current.id, answer, company, role })
      setEvaluation(r.data)
    } finally { setLoading(false) }
  }

  return (
    <div className="space-y-6">
      {/* Generate panel */}
      <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5">
        <p className="text-sm font-medium text-white/60 mb-3">Generate questions for a specific company</p>
        <div className="flex gap-3 flex-wrap">
          <input value={company} onChange={e => setCompany(e.target.value)} placeholder="Company (e.g. Google)"
            className="flex-1 min-w-36 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 transition-all" />
          <input value={role} onChange={e => setRole(e.target.value)} placeholder="Role (e.g. SDE-1)"
            className="flex-1 min-w-36 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 transition-all" />
          <button onClick={generateCustom} disabled={genLoading || !company || !role}
            className="bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center gap-2">
            {genLoading ? <Loader2 size={14} className="animate-spin" /> : <Brain size={14} />} Generate
          </button>
          <button onClick={loadDefault} disabled={genLoading}
            className="bg-white/5 hover:bg-white/10 text-white/60 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors">
            Default
          </button>
        </div>
      </div>

      {questions.length > 0 && (
        <div className="grid lg:grid-cols-3 gap-4">
          {/* Question list */}
          <div className="space-y-2">
            {questions.map((q, i) => (
              <button key={q.id} onClick={() => { setCurrent(q); setEvaluation(null); setAnswer('') }}
                className={`w-full text-left px-4 py-3 rounded-xl border text-sm transition-all ${current?.id === q.id ? 'bg-violet-500/15 border-violet-500/30 text-violet-300' : 'bg-white/3 border-white/5 text-white/60 hover:text-white hover:bg-white/5'}`}>
                <span className="font-medium">Q{i + 1}.</span> {q.question.slice(0, 60)}...
              </button>
            ))}
          </div>

          {/* Answer area */}
          <div className="lg:col-span-2 space-y-4">
            {current && (
              <>
                <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5">
                  <p className="text-white font-medium leading-relaxed">{current.question}</p>
                  {current.focus && <p className="text-xs text-white/30 mt-2">Focus: {current.focus}</p>}
                </div>

                <textarea value={answer} onChange={e => setAnswer(e.target.value)}
                  placeholder="Type your answer using the STAR method (Situation → Task → Action → Result)..."
                  rows={6}
                  className="w-full bg-[#13151f] border border-white/5 rounded-2xl px-5 py-4 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-violet-500/30 transition-all resize-none"
                />

                <button onClick={evaluate} disabled={loading || !answer.trim()}
                  className="flex items-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-40 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all shadow-lg shadow-violet-500/20">
                  {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                  Evaluate Answer
                </button>

                {evaluation && (
                  <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5 space-y-4">
                    {/* Score */}
                    <div className="flex items-center gap-4">
                      <div className="text-3xl font-bold text-white">{evaluation.score}<span className="text-base text-white/30">/100</span></div>
                      <div className="flex-1">
                        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-violet-500 to-indigo-500 rounded-full transition-all" style={{ width: `${evaluation.score}%` }} />
                        </div>
                      </div>
                    </div>

                    {/* STAR breakdown */}
                    {evaluation.star_breakdown && (
                      <div className="grid grid-cols-4 gap-2">
                        {Object.entries(evaluation.star_breakdown).map(([k, v]) => (
                          <div key={k} className="bg-white/3 rounded-xl p-3 text-center">
                            <p className="text-lg font-bold text-white">{v}</p>
                            <p className="text-[10px] text-white/30 uppercase mt-0.5">{k}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="space-y-2 text-sm">
                      <p className="text-white/70">{evaluation.feedback}</p>
                      {evaluation.missing && <p className="text-amber-400/80"><span className="font-medium">Missing:</span> {evaluation.missing}</p>}
                      {evaluation.model_answer_tip && <p className="text-emerald-400/80"><span className="font-medium">Tip:</span> {evaluation.model_answer_tip}</p>}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {questions.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <Brain size={40} className="text-white/10" />
          <p className="text-white/30 text-sm">Generate questions to start practicing</p>
        </div>
      )}
    </div>
  )
}

// ── TECHNICAL TAB ────────────────────────────────────────
function TechnicalTab() {
  const [problems, setProblems] = useState([])
  const [current, setCurrent] = useState(null)
  const [code, setCode] = useState('')
  const [hint, setHint] = useState('')
  const [hintMsg, setHintMsg] = useState('')
  const [evaluation, setEvaluation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [hintLoading, setHintLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)

  const loadProblems = async () => {
    setLoaded(true)
    const r = await AI_API.get('/api/technical/problems')
    setProblems(r.data)
    selectProblem(r.data[0])
  }

  const selectProblem = (p) => {
    setCurrent(p); setCode(p.starter); setEvaluation(null); setHint('')
  }

  const getHint = async () => {
    if (!hintMsg.trim()) return
    setHintLoading(true)
    try {
      const r = await AI_API.post('/api/technical/hint', { problemId: current.id, code, message: hintMsg })
      setHint(r.data.reply); setHintMsg('')
    } finally { setHintLoading(false) }
  }

  const evaluate = async () => {
    setLoading(true)
    try {
      const r = await AI_API.post('/api/technical/evaluate', { problemId: current.id, code })
      setEvaluation(r.data)
    } finally { setLoading(false) }
  }

  const DIFF_COLORS = { Easy: 'text-emerald-400', Medium: 'text-amber-400', Hard: 'text-red-400' }

  if (!loaded) return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <Code2 size={40} className="text-white/10" />
      <p className="text-white/30 text-sm">Practice coding problems with AI hints</p>
      <button onClick={loadProblems} className="bg-violet-600 hover:bg-violet-500 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors flex items-center gap-2">
        <ChevronRight size={16} /> Load Problems
      </button>
    </div>
  )

  return (
    <div className="grid lg:grid-cols-3 gap-4">
      {/* Problem list */}
      <div className="space-y-2">
        {problems.map(p => (
          <button key={p.id} onClick={() => selectProblem(p)}
            className={`w-full text-left px-4 py-3 rounded-xl border text-sm transition-all ${current?.id === p.id ? 'bg-violet-500/15 border-violet-500/30' : 'bg-white/3 border-white/5 hover:bg-white/5'}`}>
            <div className="flex items-center justify-between mb-1">
              <span className="font-medium text-white">{p.title}</span>
              <span className={`text-xs font-medium ${DIFF_COLORS[p.difficulty]}`}>{p.difficulty}</span>
            </div>
            <span className="text-xs text-white/30">{p.topic}</span>
          </button>
        ))}
      </div>

      {/* Editor area */}
      {current && (
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <h3 className="font-semibold text-white">{current.title}</h3>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full bg-white/5 ${DIFF_COLORS[current.difficulty]}`}>{current.difficulty}</span>
            </div>
            <p className="text-sm text-white/60 leading-relaxed">{current.description}</p>
            <p className="text-xs text-white/30 mt-3 font-mono">{current.examples}</p>
          </div>

          <textarea value={code} onChange={e => setCode(e.target.value)} rows={10}
            className="w-full bg-[#0d0f16] border border-white/5 rounded-2xl px-5 py-4 text-sm text-emerald-300 placeholder:text-white/20 focus:outline-none focus:border-violet-500/30 transition-all resize-none font-mono"
          />

          <div className="flex gap-3">
            <button onClick={evaluate} disabled={loading}
              className="flex items-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-40 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all shadow-lg shadow-violet-500/20">
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Star size={16} />} Evaluate
            </button>
            <button onClick={() => { setCode(current.starter); setEvaluation(null) }}
              className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-white/60 px-4 py-2.5 rounded-xl text-sm transition-colors">
              <RotateCcw size={14} /> Reset
            </button>
          </div>

          {/* Hint box */}
          <div className="bg-[#13151f] border border-white/5 rounded-2xl p-4 space-y-3">
            <p className="text-xs font-medium text-white/40 uppercase tracking-wider">Ask for a hint</p>
            {hint && <p className="text-sm text-white/70 bg-violet-500/5 border border-violet-500/10 rounded-xl p-3">{hint}</p>}
            <div className="flex gap-2">
              <input value={hintMsg} onChange={e => setHintMsg(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && getHint()}
                placeholder="e.g. What data structure should I use?"
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-violet-500/50 transition-all"
              />
              <button onClick={getHint} disabled={hintLoading}
                className="bg-white/5 hover:bg-violet-500/20 border border-white/10 hover:border-violet-500/30 text-white/60 hover:text-violet-400 px-3 py-2.5 rounded-xl transition-all">
                {hintLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              </button>
            </div>
          </div>

          {evaluation && (
            <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5 space-y-3">
              <div className="flex items-center gap-4">
                <div className="text-3xl font-bold text-white">{evaluation.score}<span className="text-base text-white/30">/100</span></div>
                <div className="space-y-1">
                  <p className="text-xs text-white/40">Time: <span className="text-white/70">{evaluation.time_complexity}</span></p>
                  <p className="text-xs text-white/40">Space: <span className="text-white/70">{evaluation.space_complexity}</span></p>
                </div>
                <span className={`ml-auto text-sm font-medium px-3 py-1 rounded-full ${evaluation.correctness === 'correct' ? 'bg-emerald-500/15 text-emerald-400' : evaluation.correctness === 'partial' ? 'bg-amber-500/15 text-amber-400' : 'bg-red-500/15 text-red-400'}`}>
                  {evaluation.correctness}
                </span>
              </div>
              <p className="text-sm text-white/60">{evaluation.feedback}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── RESUME TAB ────────────────────────────────────────────
function ResumeTab() {
  const [resume, setResume] = useState('')
  const [jd, setJd] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const analyze = async () => {
    if (!resume.trim() || !jd.trim()) return
    setLoading(true)
    try {
      const r = await AI_API.post('/api/resume/analyze', { resume, jobDescription: jd })
      setResult(r.data)
    } finally { setLoading(false) }
  }

  return (
    <div className="space-y-6">
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-xs font-medium text-white/40 uppercase tracking-wider">Your Resume</label>
          <textarea value={resume} onChange={e => setResume(e.target.value)} rows={12}
            placeholder="Paste your resume text here..."
            className="w-full bg-[#13151f] border border-white/5 rounded-2xl px-5 py-4 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-violet-500/30 transition-all resize-none"
          />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-medium text-white/40 uppercase tracking-wider">Job Description</label>
          <textarea value={jd} onChange={e => setJd(e.target.value)} rows={12}
            placeholder="Paste the job description here..."
            className="w-full bg-[#13151f] border border-white/5 rounded-2xl px-5 py-4 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-violet-500/30 transition-all resize-none"
          />
        </div>
      </div>

      <button onClick={analyze} disabled={loading || !resume.trim() || !jd.trim()}
        className="flex items-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-40 text-white px-6 py-3 rounded-xl text-sm font-semibold transition-all shadow-lg shadow-violet-500/20">
        {loading ? <Loader2 size={16} className="animate-spin" /> : <FileText size={16} />} Analyze Match
      </button>

      {result && (
        <div className="space-y-4">
          {/* Score cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Overall Match', value: result.match_score },
              { label: 'Keywords',      value: result.keyword_match },
              { label: 'Experience',    value: result.experience_match },
              { label: 'Skills',        value: result.skills_match },
            ].map(s => (
              <div key={s.label} className="bg-[#13151f] border border-white/5 rounded-2xl p-4 text-center">
                <div className="text-3xl font-bold text-white mb-1">{s.value}<span className="text-sm text-white/30">%</span></div>
                <div className="h-1.5 bg-white/10 rounded-full overflow-hidden mb-2">
                  <div className="h-full bg-gradient-to-r from-violet-500 to-indigo-500 rounded-full" style={{ width: `${s.value}%` }} />
                </div>
                <p className="text-xs text-white/40">{s.label}</p>
              </div>
            ))}
          </div>

          <div className="grid lg:grid-cols-3 gap-4">
            {/* Matched keywords */}
            <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5">
              <p className="text-xs font-medium text-emerald-400 uppercase tracking-wider mb-3">✓ Matched Keywords</p>
              <div className="flex flex-wrap gap-2">
                {result.matched_keywords?.map(k => (
                  <span key={k} className="text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-2.5 py-1 rounded-full">{k}</span>
                ))}
              </div>
            </div>

            {/* Missing keywords */}
            <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5">
              <p className="text-xs font-medium text-red-400 uppercase tracking-wider mb-3">✗ Missing Keywords</p>
              <div className="flex flex-wrap gap-2">
                {result.missing_keywords?.map(k => (
                  <span key={k} className="text-xs bg-red-500/10 border border-red-500/20 text-red-400 px-2.5 py-1 rounded-full">{k}</span>
                ))}
              </div>
            </div>

            {/* Suggestions */}
            <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5">
              <p className="text-xs font-medium text-violet-400 uppercase tracking-wider mb-3">↑ Suggestions</p>
              <ul className="space-y-2">
                {result.suggestions?.map((s, i) => (
                  <li key={i} className="text-xs text-white/60 flex items-start gap-2">
                    <span className="text-violet-400 mt-0.5">•</span> {s}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── MAIN COMPONENT ───────────────────────────────────────
export default function InterviewPrep() {
  const [tab, setTab] = useState('hr')

  return (
    <div className="space-y-6 font-['Sora',sans-serif]">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Interview Prep</h1>
        <p className="text-white/40 text-sm mt-0.5">Practice HR, technical interviews and analyze your resume</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 bg-[#13151f] border border-white/5 rounded-2xl p-1.5 w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${tab === id ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/25' : 'text-white/40 hover:text-white'}`}>
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {tab === 'hr'        && <HRTab />}
      {tab === 'technical' && <TechnicalTab />}
      {tab === 'resume'    && <ResumeTab />}
    </div>
  )
}