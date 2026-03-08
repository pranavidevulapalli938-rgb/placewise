import { useEffect, useState } from 'react'
import { API } from '../context/AuthContext'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'
import { Loader2, TrendingUp, Target, Award } from 'lucide-react'

const STATUS_COLORS = {
  'Applied':             '#60a5fa',
  'OA Received':         '#fbbf24',
  'Interview Scheduled': '#a78bfa',
  'Selected':            '#34d399',
  'Rejected':            '#f87171',
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#1a1d2e] border border-white/10 rounded-xl px-4 py-3 text-sm shadow-xl">
        <p className="text-white font-medium">{label || payload[0].name}</p>
        <p className="text-white/60 mt-1">{payload[0].value} applications</p>
      </div>
    )
  }
  return null
}

export default function Analytics() {
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    API.get('/applications').then(r => setApps(r.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 size={28} className="animate-spin text-violet-400" />
    </div>
  )

  // Status distribution for pie chart
  const statusData = Object.entries(
    apps.reduce((acc, a) => ({ ...acc, [a.status]: (acc[a.status] || 0) + 1 }), {})
  ).map(([name, value]) => ({ name, value }))

  // Applications over time (by week)
  const timeData = (() => {
    const grouped = {}
    apps.forEach(a => {
      const date = a.applied_date ? new Date(a.applied_date) : new Date()
      const week = `${date.getMonth() + 1}/${date.getDate()}`
      grouped[week] = (grouped[week] || 0) + 1
    })
    return Object.entries(grouped).slice(-8).map(([date, count]) => ({ date, count }))
  })()

  // Company frequency
  const companyData = Object.entries(
    apps.reduce((acc, a) => ({ ...acc, [a.company]: (acc[a.company] || 0) + 1 }), {})
  ).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([company, count]) => ({ company: company.slice(0, 12), count }))

  const total    = apps.length
  const selected = apps.filter(a => a.status === 'Selected').length
  const active   = apps.filter(a => !['Selected', 'Rejected'].includes(a.status)).length
  const successRate = total > 0 ? Math.round((selected / total) * 100) : 0

  return (
    <div className="space-y-6 font-['Sora',sans-serif]">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Analytics</h1>
        <p className="text-white/40 text-sm mt-0.5">Insights into your placement journey</p>
      </div>

      {apps.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <TrendingUp size={40} className="text-white/10" />
          <p className="text-white/30 text-sm">Add applications to see analytics</p>
        </div>
      ) : (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5 text-center">
              <TrendingUp size={20} className="text-blue-400 mx-auto mb-2" />
              <p className="text-3xl font-bold text-white">{total}</p>
              <p className="text-xs text-white/40 mt-1">Total Applications</p>
            </div>
            <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5 text-center">
              <Target size={20} className="text-violet-400 mx-auto mb-2" />
              <p className="text-3xl font-bold text-white">{active}</p>
              <p className="text-xs text-white/40 mt-1">Active Pipeline</p>
            </div>
            <div className="bg-[#13151f] border border-white/5 rounded-2xl p-5 text-center">
              <Award size={20} className="text-emerald-400 mx-auto mb-2" />
              <p className="text-3xl font-bold text-white">{successRate}%</p>
              <p className="text-xs text-white/40 mt-1">Success Rate</p>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            {/* Pie chart */}
            <div className="bg-[#13151f] border border-white/5 rounded-2xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Status Distribution</h3>
              <div className="flex items-center gap-6">
                <ResponsiveContainer width={160} height={160}>
                  <PieChart>
                    <Pie data={statusData} cx="50%" cy="50%" innerRadius={45} outerRadius={75} dataKey="value" strokeWidth={0}>
                      {statusData.map(entry => (
                        <Cell key={entry.name} fill={STATUS_COLORS[entry.name] || '#6366f1'} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2 flex-1">
                  {statusData.map(s => (
                    <div key={s.name} className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: STATUS_COLORS[s.name] || '#6366f1' }} />
                      <span className="text-xs text-white/50 flex-1 truncate">{s.name}</span>
                      <span className="text-xs font-medium text-white">{s.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Bar chart - companies */}
            <div className="bg-[#13151f] border border-white/5 rounded-2xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Top Companies Applied</h3>
              {companyData.length > 0 ? (
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={companyData} barSize={20}>
                    <XAxis dataKey="company" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="count" fill="url(#barGrad)" radius={[6, 6, 0, 0]} />
                    <defs>
                      <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#8b5cf6" />
                        <stop offset="100%" stopColor="#4f46e5" />
                      </linearGradient>
                    </defs>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-white/20 text-sm text-center py-8">Not enough data</p>
              )}
            </div>

            {/* Line chart - over time */}
            {timeData.length > 1 && (
              <div className="bg-[#13151f] border border-white/5 rounded-2xl p-6 lg:col-span-2">
                <h3 className="text-sm font-semibold text-white mb-4">Applications Over Time</h3>
                <ResponsiveContainer width="100%" height={160}>
                  <LineChart data={timeData}>
                    <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Line type="monotone" dataKey="count" stroke="#8b5cf6" strokeWidth={2.5} dot={{ fill: '#8b5cf6', strokeWidth: 0, r: 4 }} activeDot={{ r: 6, fill: '#a78bfa' }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}