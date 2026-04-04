import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Radio, Bell, Database, BarChart3,
  ChevronLeft, ChevronRight, Activity, Zap
} from 'lucide-react'
import { useUI } from '../context/UIContext'
import { useSources } from '../context/SourcesContext'
import { fetchHealth } from '../lib/api'
import { relativeTime } from '../lib/utils'

const NAV = [
  { to: '/',          icon: LayoutDashboard, label: 'Command Center' },
  { to: '/signals',   icon: Radio,           label: 'Signals Feed' },
  { to: '/alerts',    icon: Bell,            label: 'Alerts' },
  { to: '/sources',   icon: Database,        label: 'Sources' },
  { to: '/analytics', icon: BarChart3,       label: 'Analytics' },
]

export default function Sidebar({ countdown }) {
  const { sidebarCollapsed, toggleSidebar } = useUI()
  const { sources, onlineCount } = useSources()
  const [live, setLive] = useState(false)

  useEffect(() => {
    const check = async () => {
      try { await fetchHealth(); setLive(true) }
      catch { setLive(false) }
    }
    check()
    const t = setInterval(check, 30000)
    return () => clearInterval(t)
  }, [])

  const w = sidebarCollapsed ? 'w-16' : 'w-64'

  return (
    <aside className={`${w} shrink-0 flex flex-col bg-[#111827] border-r border-[#1e2d45] transition-all duration-300 ease-in-out relative`}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-[#1e2d45]">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500 to-purple-600 flex items-center justify-center shrink-0">
          <Zap size={16} className="text-white" />
        </div>
        {!sidebarCollapsed && (
          <div>
            <p className="font-bold text-white tracking-wider text-sm">GHOST<span className="text-red-400">GRID</span></p>
            <p className="text-[10px] text-slate-500 tracking-widest uppercase">Crisis Monitor</p>
          </div>
        )}
      </div>

      {/* LIVE badge */}
      {!sidebarCollapsed && (
        <div className="px-4 py-3 border-b border-[#1e2d45]">
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono font-bold tracking-widest
            ${live ? 'bg-green-500/15 text-green-400 border border-green-500/30' : 'bg-red-500/15 text-red-400 border border-red-500/30'}`}>
            <span className={`w-2 h-2 rounded-full ${live ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
            {live ? 'LIVE' : 'OFFLINE'}
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 group
              ${isActive
                ? 'bg-gradient-to-r from-red-500/20 to-purple-500/10 text-white border border-red-500/20'
                : 'text-slate-400 hover:text-white hover:bg-white/5'}`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={18} className={isActive ? 'text-red-400' : 'text-slate-500 group-hover:text-slate-300'} />
                {!sidebarCollapsed && <span className="font-medium">{label}</span>}
                {!sidebarCollapsed && isActive && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-red-400" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Source health dots */}
      {!sidebarCollapsed && (
        <div className="px-4 py-3 border-t border-[#1e2d45]">
          <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-2">Sources</p>
          <div className="flex flex-wrap gap-1.5">
            {sources.slice(0, 8).map((s, i) => {
              const age = s.last_seen ? Date.now() - new Date(s.last_seen).getTime() : Infinity
              const color = age < 3600000 ? 'bg-green-400' : age < 86400000 ? 'bg-amber-400' : 'bg-red-400'
              return (
                <div key={i} title={`${s.source}: ${relativeTime(s.last_seen)}`}
                  className={`w-2 h-2 rounded-full ${color} animate-pulse`} />
              )
            })}
          </div>
          <p className="text-[10px] text-slate-500 mt-1.5">
            {onlineCount} / {sources.length} online
          </p>
        </div>
      )}

      {/* Footer: countdown */}
      <div className="px-4 py-3 border-t border-[#1e2d45]">
        {!sidebarCollapsed ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
              <Activity size={11} />
              <span>Refresh in {countdown}s</span>
            </div>
            <button onClick={toggleSidebar} className="text-slate-500 hover:text-slate-300 transition-colors">
              <ChevronLeft size={16} />
            </button>
          </div>
        ) : (
          <button onClick={toggleSidebar} className="w-full flex justify-center text-slate-500 hover:text-slate-300 transition-colors">
            <ChevronRight size={16} />
          </button>
        )}
      </div>
    </aside>
  )
}
