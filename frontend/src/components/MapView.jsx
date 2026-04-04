/**
 * MapView.jsx — GhostGrid Interactive Signal Map
 * ================================================
 * Built with react-leaflet + Leaflet.js.
 * Renders geolocated crisis signals as colour-coded circle markers on a
 * dark CartoDB tile layer, matching the GhostGrid design system.
 *
 * Data source
 * -----------
 * Currently reads from the `useAlerts()` context which polls the backend's
 * GET /api/alerts endpoint every 30 s.
 *
 * TODO (Future-Proofing — Live Data Hook)
 * ----------------------------------------
 * The `signals` array below is derived from `alerts` (real context data).
 * When the backend's dedicated alert-geolocation endpoint is ready, replace
 * the derivation below with a direct fetch call:
 *
 *   const [signals, setSignals] = useState([])
 *   useEffect(() => {
 *     fetch('http://localhost:8000/api/alerts')
 *       .then(r => r.json())
 *       .then(data => setSignals(data.alerts ?? data))
 *       .catch(console.error)
 *   }, [])
 *
 * This will give MapView its own independent refresh cycle and allow
 * custom query params (e.g. severity filter, time window) per map view.
 */

import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useAlerts } from '../context/AlertsContext'

// ── Coordinate lookup (mirrors CommandCenter LOCATION_COORDS) ─────────────────
// Format: [lat, lng]
const LOCATION_COORDS = {
  'mumbai':    [19.0760,  72.8777],
  'delhi':     [28.6139,  77.2090],
  'hyderabad': [17.3850,  78.4867],
  'karachi':   [24.8607,  67.0099],
  'dhaka':     [23.8103,  90.4125],
  'nairobi':   [-1.2921,  36.8219],
  'dubai':     [25.2048,  55.2708],
  'singapore': [1.3521,  103.8198],
  'london':    [51.5074,  -0.1276],
  'new york':  [40.7128, -74.0060],
  'shanghai':  [31.2304, 121.4737],
  'cairo':     [30.0444,  31.2357],
  'lahore':    [31.5204,  74.3587],
  'islamabad': [33.6844,  73.0479],
  'kolkata':   [22.5726,  88.3639],
  'chennai':   [13.0827,  80.2707],
  'bangkok':   [13.7563, 100.5018],
  'jakarta':   [-6.2088, 106.8456],
  'tokyo':     [35.6762, 139.6503],
  'beijing':   [39.9042, 116.4074],
  'moscow':    [55.7558,  37.6173],
  'istanbul':  [41.0082,  28.9784],
  'lagos':     [6.5244,    3.3792],
  'paris':     [48.8566,   2.3522],
}

// ── Severity → marker colour (matches GhostGrid CSS vars) ─────────────────────
const SEVERITY_COLOUR = {
  high:   '#E24B4A',
  medium: '#EF9F27',
  low:    '#378ADD',
}

function getSeverityColour(severity) {
  return SEVERITY_COLOUR[severity] ?? '#378ADD'
}

// ── Auto-fit bounds when signals change ───────────────────────────────────────
function BoundsFitter({ positions }) {
  const map = useMap()
  useEffect(() => {
    if (positions.length > 0) {
      try {
        const L = window.L
        if (L) {
          const bounds = L.latLngBounds(positions)
          map.fitBounds(bounds, { padding: [40, 40], maxZoom: 6 })
        }
      } catch (_) {
        // If bounds fitting fails, stay on default view
      }
    }
  }, [positions, map])
  return null
}

// ── Main MapView component ────────────────────────────────────────────────────
export default function MapView() {
  const { alerts } = useAlerts()

  // ── Derive signals from alert data ──────────────────────────────────────────
  // TODO (Future-Proofing): Replace this derivation with a direct fetch to
  // http://localhost:8000/api/alerts when the dedicated geolocation endpoint
  // is ready (see file header for full fetch snippet).
  const signalMap = {}
  for (const alert of alerts) {
    const key = (alert.location ?? '').toLowerCase().trim()
    if (!key || key === 'unknown' || key === 'global') continue
    const coords = LOCATION_COORDS[key]
    if (!coords) continue

    if (!signalMap[key]) {
      signalMap[key] = {
        location: alert.location,
        lat: coords[0],
        lng: coords[1],
        alerts: [],
        worstSeverity: 'low',
      }
    }
    signalMap[key].alerts.push(alert)

    // Escalate severity: high > medium > low
    const order = { high: 2, medium: 1, low: 0 }
    if ((order[alert.severity] ?? 0) > (order[signalMap[key].worstSeverity] ?? 0)) {
      signalMap[key].worstSeverity = alert.severity
    }
  }
  const signals = Object.values(signalMap)
  const positions = signals.map(s => [s.lat, s.lng])

  return (
    <div className="card h-full flex flex-col overflow-hidden" style={{ minHeight: 0 }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e2d45] shrink-0">
        <p className="text-slate-400 text-xs uppercase tracking-widest">
          Global Signal Map
        </p>
        <div className="flex items-center gap-2">
          {signals.length > 0 && (
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
          )}
          <span className="text-slate-500 text-[10px] font-mono">
            {signals.length} location{signals.length !== 1 ? 's' : ''} active
          </span>
        </div>
      </div>

      {/* Leaflet Map */}
      <div className="flex-1 relative" style={{ minHeight: 0 }}>
        <MapContainer
          center={[20, 20]}
          zoom={2}
          minZoom={2}
          maxZoom={10}
          style={{ height: '100%', width: '100%', background: '#0a0f1a' }}
          zoomControl={false}
          attributionControl={false}
        >
          {/* Dark CartoDB tile layer — matches GhostGrid theme */}
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com">CARTO</a>'
          />

          {/* Auto-fit to active signals */}
          {positions.length > 0 && <BoundsFitter positions={positions} />}

          {/* Signal markers */}
          {signals.map((signal) => {
            const colour    = getSeverityColour(signal.worstSeverity)
            const count     = signal.alerts.length
            const topAlert  = signal.alerts.sort((a, b) => {
              const order = { high: 2, medium: 1, low: 0 }
              return (order[b.severity] ?? 0) - (order[a.severity] ?? 0)
            })[0]

            return (
              <CircleMarker
                key={signal.location}
                center={[signal.lat, signal.lng]}
                radius={count > 3 ? 14 : count > 1 ? 10 : 7}
                pathOptions={{
                  color:       colour,
                  fillColor:   colour,
                  fillOpacity: 0.55,
                  weight:      1.5,
                  opacity:     0.9,
                }}
              >
                <Popup className="ghost-popup">
                  <div style={{
                    fontFamily: "'Inter', system-ui, sans-serif",
                    minWidth: 180,
                  }}>
                    {/* Location header */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      marginBottom: 10,
                      paddingBottom: 8,
                      borderBottom: '1px solid #1e2d45',
                    }}>
                      <span style={{
                        width: 8, height: 8,
                        borderRadius: '50%',
                        backgroundColor: colour,
                        boxShadow: `0 0 8px ${colour}99`,
                        flexShrink: 0,
                      }} />
                      <span style={{ color: '#e2e8f0', fontWeight: 700, fontSize: 13, textTransform: 'capitalize' }}>
                        {signal.location}
                      </span>
                      <span style={{
                        marginLeft: 'auto',
                        fontSize: 10,
                        fontWeight: 700,
                        fontFamily: 'monospace',
                        padding: '2px 6px',
                        borderRadius: 4,
                        backgroundColor: `${colour}22`,
                        color: colour,
                        border: `1px solid ${colour}44`,
                        textTransform: 'uppercase',
                      }}>
                        {signal.worstSeverity}
                      </span>
                    </div>

                    {/* Signal count */}
                    <div style={{ color: '#64748b', fontSize: 11, marginBottom: 8, fontFamily: 'monospace' }}>
                      {count} active signal{count !== 1 ? 's' : ''}
                    </div>

                    {/* Top alert preview */}
                    {topAlert && (
                      <div>
                        <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                          Latest
                        </div>
                        <div style={{ color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>
                          {(topAlert.text || topAlert.message || '—').slice(0, 80)}
                          {(topAlert.text || topAlert.message || '').length > 80 ? '…' : ''}
                        </div>
                        {topAlert.commodity && (
                          <div style={{
                            marginTop: 8,
                            display: 'inline-block',
                            fontSize: 10,
                            fontFamily: 'monospace',
                            padding: '2px 6px',
                            borderRadius: 4,
                            backgroundColor: 'rgba(55,138,221,0.12)',
                            color: '#378ADD',
                            border: '1px solid rgba(55,138,221,0.25)',
                          }}>
                            {topAlert.commodity}
                          </div>
                        )}
                        {topAlert.confidence != null && (
                          <div style={{
                            marginTop: 6,
                            fontSize: 10,
                            fontFamily: 'monospace',
                            color: '#64748b',
                          }}>
                            Confidence: {Math.round(topAlert.confidence * 100)}%
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>

        {/* Empty-state overlay */}
        {signals.length === 0 && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            pointerEvents: 'none', zIndex: 1000,
            background: 'rgba(10,15,26,0.6)',
          }}>
            <div style={{
              width: 52, height: 52, borderRadius: '50%',
              background: 'rgba(55,138,221,0.07)',
              border: '1px solid rgba(55,138,221,0.18)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: 12,
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#378ADD" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10"/>
                <line x1="2" y1="12" x2="22" y2="12"/>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
              </svg>
            </div>
            <p style={{ color: '#94a3b8', fontSize: 13, fontWeight: 600, letterSpacing: '0.05em', marginBottom: 4 }}>
              No Active Signals
            </p>
            <p style={{ color: '#334155', fontSize: 11, fontFamily: 'monospace' }}>
              Awaiting data from monitored regions…
            </p>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 px-4 py-2 border-t border-[#1e2d45] shrink-0">
        {Object.entries(SEVERITY_COLOUR).map(([sev, colour]) => (
          <div key={sev} className="flex items-center gap-1.5">
            <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: colour, display: 'inline-block' }} />
            <span className="text-slate-500 text-[10px] font-mono capitalize">{sev}</span>
          </div>
        ))}
        <span className="ml-auto text-[10px] font-mono text-slate-600">react-leaflet</span>
      </div>
    </div>
  )
}
