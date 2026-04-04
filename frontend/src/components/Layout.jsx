import { useState, useEffect, useCallback } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import AlertDrawer from './AlertDrawer'
import Toast from './Toast'
import GlobalSearch from './GlobalSearch'
import { useUI } from '../context/UIContext'
import { useAlerts } from '../context/AlertsContext'
import { useSources } from '../context/SourcesContext'

const REFRESH_INTERVAL = 30

export default function Layout() {
  const { activeDrawerSignal, closeDrawer, toasts, removeToast } = useUI()
  const { loadAlerts } = useAlerts()
  const { loadSources } = useSources()
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL)
  const [searchOpen, setSearchOpen] = useState(false)

  const refresh = useCallback(() => {
    loadAlerts()
    loadSources()
    setCountdown(REFRESH_INTERVAL)
  }, [loadAlerts, loadSources])

  // Initial load
  useEffect(() => { refresh() }, [])

  // Countdown + auto-refresh
  useEffect(() => {
    const tick = setInterval(() => {
      setCountdown(c => {
        if (c <= 1) { refresh(); return REFRESH_INTERVAL }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(tick)
  }, [refresh])

  // Cmd+K listener
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen(p => !p)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#000000' }}>
      <Sidebar countdown={countdown} />

      <main className="flex-1 overflow-hidden relative" style={{ background: '#000000' }}>
        <Outlet />
      </main>

      {activeDrawerSignal && (
        <AlertDrawer signal={activeDrawerSignal} onClose={closeDrawer} />
      )}

      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-50 space-y-1 max-w-sm">
        {toasts.map(t => (
          <Toast key={t.id} toast={t} onDismiss={() => removeToast(t.id)} />
        ))}
      </div>

      {searchOpen && <GlobalSearch onClose={() => setSearchOpen(false)} />}
    </div>
  )
}
