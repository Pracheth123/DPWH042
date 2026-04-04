import { confidenceColor } from '../lib/utils'

export default function ConfidenceBar({ value, height = 4, showLabel = false }) {
  const pct = Math.round((value ?? 0) * 100)
  const color = confidenceColor(value ?? 0)

  return (
    <div className="flex items-center gap-2 w-full">
      <div className={`flex-1 bg-white/10 rounded-full overflow-hidden`} style={{ height }}>
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-mono shrink-0" style={{ color }}>
          {pct}%
        </span>
      )}
    </div>
  )
}
