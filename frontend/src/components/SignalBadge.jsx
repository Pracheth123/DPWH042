import { getSignalConfig, getSeverityConfig } from '../lib/utils'

export function SignalBadge({ type }) {
  const c = getSignalConfig(type)
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold font-mono ${c.bg} ${c.text} border ${c.border}`}>
      {c.label}
    </span>
  )
}

export function SeverityBadge({ severity }) {
  const c = getSeverityConfig(severity)
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${c.bg} ${c.text} border ${c.border}`}>
      {c.label}
    </span>
  )
}
