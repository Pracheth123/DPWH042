import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'

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
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      whileHover={{ scale: 1.02, y: -2, transition: { duration: 0.2 } }}
      className="card p-5 flex items-start gap-4 relative overflow-hidden cursor-default"
    >
      {/* Colour-tinted glow on hover */}
      <div className="absolute inset-0 opacity-0 hover:opacity-100 transition-opacity pointer-events-none"
        style={{ background: `radial-gradient(ellipse at 0% 0%, ${color}12, transparent 60%)` }} />

      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${color}18`, border: `1px solid ${color}28` }}>
        <Icon size={20} style={{ color }} />
      </div>

      <div className="relative">
        <p className="text-white/40 text-xs uppercase tracking-widest">{label}</p>
        <p className="text-white text-2xl font-bold font-mono mt-0.5">
          {typeof value === 'number' ? displayed : value}
        </p>
        {subtitle && <p className="text-white/25 text-xs mt-0.5">{subtitle}</p>}
      </div>
    </motion.div>
  )
}
