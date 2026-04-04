import { useEffect, useState } from 'react'
import { X, AlertTriangle, Info, CheckCircle } from 'lucide-react'

const CONFIG = {
  high:    { icon: AlertTriangle, bar: 'bg-red-500',    bg: 'bg-[#1a2235] border-red-500/40',   text: 'text-red-400' },
  warning: { icon: AlertTriangle, bar: 'bg-amber-500',  bg: 'bg-[#1a2235] border-amber-500/40', text: 'text-amber-400' },
  info:    { icon: Info,          bar: 'bg-blue-500',   bg: 'bg-[#1a2235] border-blue-500/40',  text: 'text-blue-400' },
  success: { icon: CheckCircle,   bar: 'bg-green-500',  bg: 'bg-[#1a2235] border-green-500/40', text: 'text-green-400' },
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
    <div className={`relative overflow-hidden rounded-lg border ${cfg.bg} shadow-xl animate-slide-in-top`}>
      <div className="flex items-start gap-3 p-4 pr-10">
        <Icon size={16} className={`${cfg.text} shrink-0 mt-0.5`} />
        <p className="text-slate-200 text-sm leading-snug">{toast.msg}</p>
      </div>
      {/* Progress bar */}
      <div className="absolute bottom-0 left-0 h-0.5 bg-white/10 w-full">
        <div
          className={`h-full ${cfg.bar} transition-none`}
          style={{ width: `${progress}%` }}
        />
      </div>
      <button
        onClick={onDismiss}
        className="absolute top-3 right-3 text-slate-500 hover:text-slate-200 transition-colors"
      >
        <X size={14} />
      </button>
    </div>
  )
}
