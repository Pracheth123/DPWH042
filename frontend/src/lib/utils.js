// ── Signal type config ────────────────────────────────────────────────────────
export const SIGNAL_CONFIG = {
  shortage_signal: { label: 'Shortage',  color: '#E24B4A', bg: 'bg-red-500/20',    text: 'text-red-400',    border: 'border-red-500/30' },
  price_hike:      { label: 'Price Hike', color: '#EF9F27', bg: 'bg-amber-500/20',  text: 'text-amber-400',  border: 'border-amber-500/30' },
  urgency_sale:    { label: 'Urgency',   color: '#7F77DD', bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/30' },
  neutral:         { label: 'Neutral',   color: '#378ADD', bg: 'bg-blue-500/20',   text: 'text-blue-400',   border: 'border-blue-500/30' },
  // legacy / alternate names
  behavior:        { label: 'Behavior',  color: '#7F77DD', bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/30' },
  price:           { label: 'Price',     color: '#EF9F27', bg: 'bg-amber-500/20',  text: 'text-amber-400',  border: 'border-amber-500/30' },
  logistics:       { label: 'Logistics', color: '#EF9F27', bg: 'bg-amber-500/20',  text: 'text-amber-400',  border: 'border-amber-500/30' },
  news:            { label: 'News',      color: '#378ADD', bg: 'bg-blue-500/20',   text: 'text-blue-400',   border: 'border-blue-500/30' },
}

export const getSignalConfig = (type) =>
  SIGNAL_CONFIG[type?.toLowerCase()] ?? SIGNAL_CONFIG.neutral

// ── Severity config ───────────────────────────────────────────────────────────
export const SEVERITY_CONFIG = {
  high:   { label: 'HIGH',   color: '#E24B4A', bg: 'bg-red-500/20',    text: 'text-red-400',    border: 'border-red-500/30',    glow: 'glow-red' },
  medium: { label: 'MED',    color: '#EF9F27', bg: 'bg-amber-500/20',  text: 'text-amber-400',  border: 'border-amber-500/30',  glow: 'glow-amber' },
  low:    { label: 'LOW',    color: '#378ADD', bg: 'bg-blue-500/20',   text: 'text-blue-400',   border: 'border-blue-500/30',   glow: 'glow-blue' },
}

export const getSeverityConfig = (sev) =>
  SEVERITY_CONFIG[sev?.toLowerCase()] ?? SEVERITY_CONFIG.low

// ── Source icons (emoji fallbacks) ────────────────────────────────────────────
export const SOURCE_ICONS = {
  telegram:     '✈',
  whatsapp:     '💬',
  olx:          '🏷',
  forum:        '💬',
  news:         '📰',
  shipping:     '🚢',
  customs:      '🛂',
  trends:       '📈',
  rss:          '📡',
  commodity_api:'📊',
  manual:       '✏️',
}

export const getSourceIcon = (src) => SOURCE_ICONS[src?.toLowerCase()] ?? '🔗'

// ── Time formatting ───────────────────────────────────────────────────────────
export const formatTime = (iso) => {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleTimeString('en-US', { hour12: false })
  } catch { return iso }
}

export const formatDateTime = (iso) => {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false,
    })
  } catch { return iso }
}

export const relativeTime = (iso) => {
  if (!iso) return '—'
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const s = Math.floor(diff / 1000)
    if (s < 60)  return `${s}s ago`
    const m = Math.floor(s / 60)
    if (m < 60)  return `${m}m ago`
    const h = Math.floor(m / 60)
    if (h < 24)  return `${h}h ago`
    return `${Math.floor(h / 24)}d ago`
  } catch { return iso }
}

// ── Confidence color ──────────────────────────────────────────────────────────
export const confidenceColor = (c) => {
  if (c == null || isNaN(c)) return '#64748b'
  if (c >= 0.75) return '#E24B4A'
  if (c >= 0.5)  return '#EF9F27'
  return '#378ADD'
}

// ── Truncate text ─────────────────────────────────────────────────────────────
export const truncate = (str, n = 80) => {
  if (!str || typeof str !== 'string') return ''
  return str.length > n ? str.slice(0, n) + '…' : str
}

// ── Get display text from alert (handles both AlertResponse and SignalRecord) ──
// AlertResponse field: text | SignalRecord fields: normalized_text, raw_text, text
export const getAlertText = (alert) =>
  alert?.normalized_text || alert?.text || alert?.raw_text || 'No signal text available'

// ── Unique ID ─────────────────────────────────────────────────────────────────
export const uid = () => Math.random().toString(36).slice(2, 9)
