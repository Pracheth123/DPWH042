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
    const steps = 30
    let step = 0
    const timer = setInterval(() => {
      step++
      setDisplayed(Math.round(start + (delta * step) / steps))
      if (step >= steps) clearInterval(timer)
    }, 16)
    return () => clearInterval(timer)
  }, [value])

  return (
    <div className="card p-5 flex items-start gap-4 relative overflow-hidden group hover:border-white/10 transition-colors">
      {/* Glow */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ background: `radial-gradient(ellipse at 0% 0%, ${color}15, transparent 60%)` }} />

      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${color}20`, border: `1px solid ${color}30` }}>
        <Icon size={20} style={{ color }} />
      </div>

      <div className="relative">
        <p className="text-slate-400 text-xs uppercase tracking-widest">{label}</p>
        <p className="text-white text-2xl font-bold font-mono mt-0.5">
          {typeof value === 'number' ? displayed : value}
        </p>
        {subtitle && <p className="text-slate-500 text-xs mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}
