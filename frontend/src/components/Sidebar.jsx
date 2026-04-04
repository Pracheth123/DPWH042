import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Radio, Bell, Database, BarChart3,
  ChevronLeft, ChevronRight, Activity, Zap, TrendingUp
} from 'lucide-react'
import { useUI } from '../context/UIContext'
import { useSources } from '../context/SourcesContext'
import { fetchHealth } from '../lib/api'
import { relativeTime } from '../lib/utils'

const NAV = [
  { to: '/',          icon: LayoutDashboard, label: 'COMMAND CTR' },
  { to: '/signals',   icon: Radio,           label: 'SIGNALS' },
  { to: '/alerts',    icon: Bell,            label: 'ALERTS' },
  { to: '/sources',   icon: Database,        label: 'SOURCES' },
  { to: '/analytics', icon: BarChart3,       label: 'ANALYTICS' },
  { to: '/simulator', icon: TrendingUp,      label: 'SIMULATOR' },
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

  const w = sidebarCollapsed ? 'w-12' : 'w-52'

  return (
    <aside
      className={`${w} shrink-0 flex flex-col transition-all duration-150`}
      style={{
        background: '#0d0d0d',
        borderRight: '1px solid #2a2a2a',
      }}
    >
      {/* ── Logo ── */}
      <div
        className="flex items-center gap-2 px-3 py-3"
        style={{ borderBottom: '1px solid #2a2a2a' }}
      >
        <div
          className="flex items-center justify-center shrink-0"
          style={{ width: 22, height: 22, background: '#00FF41', color: '#000' }}
        >
          <Zap size={13} />
        </div>
        {!sidebarCollapsed && (
          <div>
            <p style={{ fontFamily: 'Fira Code, monospace', fontSize: 12, fontWeight: 700, color: '#00FF41', letterSpacing: '0.12em' }}>
              GHOST<span style={{ color: '#e0e0e0' }}>GRID</span>
            </p>
            <p style={{ fontFamily: 'Fira Code, monospace', fontSize: 9, color: '#444', letterSpacing: '0.1em', marginTop: 1 }}>
              CRISIS/MONITOR v3.0
            </p>
          </div>
        )}
      </div>

      {/* ── Status bar ── */}
      {!sidebarCollapsed && (
        <div
          className="flex items-center gap-2 px-3 py-2"
          style={{ borderBottom: '1px solid #2a2a2a', background: '#080808' }}
        >
          <span
            style={{
              width: 6, height: 6, flexShrink: 0,
              background: live ? '#00FF41' : '#E24B4A',
              animation: live ? 'termBlink 1.4s step-end infinite' : 'none',
            }}
          />
          <span style={{ fontFamily: 'Fira Code, monospace', fontSize: 10, color: live ? '#00FF41' : '#E24B4A', letterSpacing: '0.1em' }}>
            {live ? 'SYS:ONLINE' : 'SYS:OFFLINE'}
          </span>
        </div>
      )}

      {/* ── Navigation ── */}
      <nav className="flex-1 py-1 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: sidebarCollapsed ? '7px 0' : '7px 12px',
              justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
              fontFamily: 'Fira Code, monospace',
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: '0.08em',
              textDecoration: 'none',
              borderLeft: isActive ? '2px solid #00FF41' : '2px solid transparent',
              background: isActive ? 'rgba(0,255,65,0.06)' : 'transparent',
              color: isActive ? '#00FF41' : '#555555',
              transition: 'all 0.1s',
            })}
            onMouseEnter={e => {
              if (!e.currentTarget.style.borderLeftColor.includes('00FF41')) {
                e.currentTarget.style.color = '#aaaaaa'
                e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
              }
            }}
            onMouseLeave={e => {
              if (!e.currentTarget.style.borderLeftColor.includes('00FF41')) {
                e.currentTarget.style.color = '#555555'
                e.currentTarget.style.background = 'transparent'
              }
            }}
          >
            <Icon size={14} />
            {!sidebarCollapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* ── Sources health ── */}
      {!sidebarCollapsed && (
        <div className="px-3 py-2" style={{ borderTop: '1px solid #2a2a2a' }}>
          <p style={{ fontFamily: 'Fira Code, monospace', fontSize: 9, color: '#444', letterSpacing: '0.1em', marginBottom: 5 }}>
            SOURCES [{onlineCount}/{sources.length}]
          </p>
          <div className="flex flex-wrap gap-1">
            {sources.slice(0, 10).map((s, i) => {
              const age = s.last_seen ? Date.now() - new Date(s.last_seen).getTime() : Infinity
              const color = age < 3600000 ? '#00FF41' : age < 86400000 ? '#EF9F27' : '#E24B4A'
              return (
                <span
                  key={i}
                  title={`${s.source}: ${relativeTime(s.last_seen)}`}
                  style={{ width: 6, height: 6, background: color, display: 'inline-block' }}
                />
              )
            })}
          </div>
        </div>
      )}

      {/* ── Footer / collapse ── */}
      <div
        className="flex items-center justify-between px-3 py-2"
        style={{ borderTop: '1px solid #2a2a2a', background: '#080808' }}
      >
        {!sidebarCollapsed ? (
          <>
            <span style={{ fontFamily: 'Fira Code, monospace', fontSize: 9, color: '#333' }}>
              SYNC/{countdown}s
            </span>
            <button
              onClick={toggleSidebar}
              style={{ color: '#444', background: 'none', border: 'none', padding: 2, lineHeight: 0 }}
              onMouseEnter={e => e.currentTarget.style.color = '#00FF41'}
              onMouseLeave={e => e.currentTarget.style.color = '#444'}
            >
              <ChevronLeft size={13} />
            </button>
          </>
        ) : (
          <button
            onClick={toggleSidebar}
            style={{ color: '#444', background: 'none', border: 'none', padding: 2, lineHeight: 0, margin: '0 auto' }}
            onMouseEnter={e => e.currentTarget.style.color = '#00FF41'}
            onMouseLeave={e => e.currentTarget.style.color = '#444'}
          >
            <ChevronRight size={13} />
          </button>
        )}
      </div>
    </aside>
  )
}
