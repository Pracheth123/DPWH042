import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Health ────────────────────────────────────────────────────────────────────
export const fetchHealth = () => api.get('/health').then(r => r.data)

// ── Alerts ────────────────────────────────────────────────────────────────────
export const fetchAlerts = (params = {}) =>
  api.get('/api/alerts', { params }).then(r => r.data)

export const fetchAlert = (id) =>
  api.get(`/api/alerts/${id}`).then(r => r.data)

// ── Sources ───────────────────────────────────────────────────────────────────
export const fetchSources = () =>
  api.get('/api/sources').then(r => r.data)

// ── Ingest (demo/test) ────────────────────────────────────────────────────────
export const ingestSignal = (payload) =>
  api.post('/api/ingest', payload).then(r => r.data)
