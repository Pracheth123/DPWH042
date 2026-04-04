import { BrowserRouter } from 'react-router-dom'
import { UIProvider } from './context/UIContext'
import { AlertsProvider } from './context/AlertsContext'
import { SourcesProvider } from './context/SourcesContext'
import AppRoutes from './AppRoutes'

export default function App() {
  return (
    <BrowserRouter>
      <UIProvider>
        <SourcesProvider>
          <AlertsProvider>
            <AppRoutes />
          </AlertsProvider>
        </SourcesProvider>
      </UIProvider>
    </BrowserRouter>
  )
}
