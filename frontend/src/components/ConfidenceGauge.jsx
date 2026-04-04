import { confidenceColor } from '../lib/utils'

export default function ConfidenceGauge({ value, size = 64 }) {
  const pct = Math.min(1, Math.max(0, value ?? 0))
  const color = confidenceColor(pct)
  const r = (size / 2) - 6
  const circ = 2 * Math.PI * r
  const dash = pct * circ
  const gap = circ - dash

  return (
    <div className="relative flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        {/* Track */}
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="4"
        />
        {/* Value */}
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${gap}`}
          style={{ transition: 'stroke-dasharray 0.6s ease-out', filter: `drop-shadow(0 0 4px ${color})` }}
        />
      </svg>
      <span
        className="absolute text-xs font-bold font-mono"
        style={{ color }}
      >
        {Math.round(pct * 100)}%
      </span>
    </div>
  )
}
