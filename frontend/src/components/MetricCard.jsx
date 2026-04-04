import { useEffect, useRef, useState } from 'react'

export default function MetricCard({ icon: Icon, label, value, color = '#378ADD', subtitle }) {
  const [displayed, setDisplayed] = useState(0)
  const targetRef = useRef(value)

  useEffect(() => {
    targetRef.current = value
    let start = displayed
    const target = Number(value) || 0
    if (isNaN(target)) { setDisplayed(value); return }
    const delta = target - start
    if (delta === 0) return
    const steps = 20
    let step = 0
    const timer = setInterval(() => {
      step++
      setDisplayed(Math.round(start + (delta * step) / steps))
      if (step >= steps) clearInterval(timer)
    }, 16)
    return () => clearInterval(timer)
  }, [value])

  return (
    <div
      style={{
        background: '#0d0d0d',
        border: `1px solid #2a2a2a`,
        borderLeft: `2px solid ${color}`,
        padding: '8px 12px',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        overflow: 'hidden',
      }}
    >
      <Icon size={16} style={{ color, flexShrink: 0 }} />
      <div>
        <p style={{ fontFamily: 'Fira Code, monospace', fontSize: 9, color: '#555', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          {label}
        </p>
        <p style={{ fontFamily: 'Fira Code, monospace', fontSize: 22, fontWeight: 700, color: '#d8d8d8', lineHeight: 1.1, marginTop: 2 }}>
          {typeof value === 'number' ? displayed : value}
        </p>
        {subtitle && (
          <p style={{ fontFamily: 'Fira Code, monospace', fontSize: 9, color: '#444', marginTop: 2 }}>{subtitle}</p>
        )}
      </div>
    </div>
  )
}
