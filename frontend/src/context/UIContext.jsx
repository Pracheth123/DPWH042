import { createContext, useContext, useState, useCallback } from 'react'
import { uid } from '../lib/utils'

const UIContext = createContext(null)

export function UIProvider({ children }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [activeDrawerSignal, setActiveDrawerSignal] = useState(null)
  const [toasts, setToasts] = useState([])

  const toggleSidebar = useCallback(() => setSidebarCollapsed(p => !p), [])

  const openDrawer = useCallback((signal) => setActiveDrawerSignal(signal), [])
  const closeDrawer = useCallback(() => setActiveDrawerSignal(null), [])

  const addToast = useCallback((msg, type = 'info') => {
    const id = uid()
    setToasts(p => [...p, { id, msg, type }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 5000)
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(p => p.filter(t => t.id !== id))
  }, [])

  return (
    <UIContext.Provider value={{
      sidebarCollapsed, toggleSidebar,
      activeDrawerSignal, openDrawer, closeDrawer,
      toasts, addToast, removeToast,
    }}>
      {children}
    </UIContext.Provider>
  )
}

export const useUI = () => useContext(UIContext)
