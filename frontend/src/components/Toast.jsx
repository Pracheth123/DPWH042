import { useEffect, useState } from 'react'
import { X, AlertTriangle, Info, CheckCircle } from 'lucide-react'

const CONFIG = {
  high:    { icon: AlertTriangle, color: '#E24B4A' },
  warning: { icon: AlertTriangle, color: '#EF9F27' },
  info:    { icon: Info,          color: '#378ADD' },
  success: { icon: CheckCircle,   color: '#00FF41' },
}

export default function Toast({ toast, onDismiss }) {
  const cfg = CONFIG[toast.type] ?? CONFIG.info
  const Icon = cfg.icon
  const [progress, setProgress] = useState(100)

  useEffect(() => {
    const start = Date.now()
    const duration = 5000
    const raf = () => {
      const elapsed = Date.now() - start
      setProgress(Math.max(0, 100 - (elapsed / duration) * 100))
      if (elapsed < duration) requestAnimationFrame(raf)
    }
    requestAnimationFrame(raf)
  }, [])

  return (
    <div
      className="animate-slide-in-top"
      style={{
        background: '#0d0d0d',
        border: `1px solid #2a2a2a`,
        borderLeft: `2px solid ${cfg.color}`,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 32px 8px 10px' }}>
        <Icon size={13} style={{ color: cfg.color, flexShrink: 0, marginTop: 1 }} />
        <p style={{ fontFamily: 'Fira Code, monospace', fontSize: 11, color: '#aaa', lineHeight: 1.4 }}>{toast.msg}</p>
      </div>
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 1, background: '#1a1a1a' }}>
        <div style={{ height: '100%', background: cfg.color, width: `${progress}%`, transition: 'none' }} />
      </div>
      <button
        onClick={onDismiss}
        style={{ position: 'absolute', top: 6, right: 6, color: '#444', background: 'none', border: 'none', lineHeight: 0, padding: 2 }}
        onMouseEnter={e => e.currentTarget.style.color = '#aaa'}
        onMouseLeave={e => e.currentTarget.style.color = '#444'}
      >
        <X size={11} />
      </button>
    </div>
  )
}
