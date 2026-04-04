import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'
import { api } from '../lib/api'
import { useUI } from './UIContext'

const AlertsContext = createContext(null)

export function AlertsProvider({ children }) {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(false)
  const [lastFetch, setLastFetch] = useState(null)
  const { addToast } = useUI()
  const prevHighCount = useRef(0)

  const loadAlerts = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/api/alerts', { params: { hours: 72, limit: 200 } })
      const list = res.data?.alerts ?? res.data ?? []
      setAlerts(list)
      setLastFetch(Date.now())

      // Toast for new HIGH alerts
      const highCount = list.filter(a => a.severity === 'high').length
      if (highCount > prevHighCount.current && prevHighCount.current > 0) {
        addToast(`🚨 ${highCount - prevHighCount.current} new HIGH alert(s)`, 'high')
      }
      prevHighCount.current = highCount
    } catch (err) {
      console.error('Failed to load alerts:', err)
    } finally {
      setLoading(false)
    }
  }, [addToast])

  // Self-contained 30s polling (fallback / initial load)
  useEffect(() => {
    loadAlerts()
    const id = setInterval(loadAlerts, 30000)
    return () => clearInterval(id)
  }, [loadAlerts])

  // WebSocket — real-time push from backend /ws/signals
  useEffect(() => {
    const wsUrl = `${import.meta.env.VITE_API_BASE_URL.replace('http', 'ws')}/ws/signals`
    const ws = new WebSocket(wsUrl)

    ws.onmessage = (event) => {
      try {
        const signal = JSON.parse(event.data)
        setAlerts(prev => {
          const next = [signal, ...prev].slice(0, 200)
          // Toast for new HIGH alerts arriving via WebSocket
          if (signal.severity === 'high' && prevHighCount.current > 0) {
            prevHighCount.current += 1
            addToast('🚨 New HIGH alert (live)', 'high')
          }
          return next
        })
      } catch (e) {
        console.warn('WS message parse error:', e)
      }
    }

    ws.onerror = () => console.warn('WS connection failed — falling back to polling')

    return () => ws.close()
  }, [addToast])

  return (
    <AlertsContext.Provider value={{ alerts, loading, lastFetch, loadAlerts }}>
      {children}
    </AlertsContext.Provider>
  )
}

export const useAlerts = () => useContext(AlertsContext)
