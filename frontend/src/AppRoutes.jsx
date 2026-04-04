import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import CommandCenter from './pages/CommandCenter'
import SignalsFeed from './pages/SignalsFeed'
import Alerts from './pages/Alerts'
import Sources from './pages/Sources'
import Analytics from './pages/Analytics'

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<CommandCenter />} />
        <Route path="signals"   element={<SignalsFeed />} />
        <Route path="alerts"    element={<Alerts />} />
        <Route path="sources"   element={<Sources />} />
        <Route path="analytics" element={<Analytics />} />
      </Route>
    </Routes>
  )
}
