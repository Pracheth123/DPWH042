import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { fetchSources } from '../lib/api'

const SourcesContext = createContext(null)

export function SourcesProvider({ children }) {
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Online: last_seen within 1h OR (no last_seen) signal_count > 0
  const onlineCount = sources.filter(s => {
    if (s.last_seen) return (Date.now() - new Date(s.last_seen).getTime()) < 3600_000
    return (s.signal_count ?? 0) > 0
  }).length

  const loadSources = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSources()
      setSources(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to load sources:', err)
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Self-contained 30s polling
  useEffect(() => {
    loadSources()
    const id = setInterval(loadSources, 30000)
    return () => clearInterval(id)
  }, [loadSources])

  return (
    <SourcesContext.Provider value={{ sources, loading, error, onlineCount, loadSources }}>
      {children}
    </SourcesContext.Provider>
  )
}

export const useSources = () => useContext(SourcesContext)
