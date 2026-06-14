import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import { ChatPage } from '@/pages/ChatPage'
import { AdminPage } from '@/pages/AdminPage'
import { LoginPage } from '@/pages/LoginPage'
import { OAuthCallback } from '@/pages/OAuthCallback'
import { useAuthStore } from '@/store/authStore'
import { usePageView } from '@/analytics'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

/** Render-null component that fires page_view on every route change. */
function RouterAnalytics() {
  usePageView()
  return null
}

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '') || '/'}>
      <RouterAnalytics />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/callback" element={<OAuthCallback />} />
        <Route path="/" element={
          <ProtectedRoute><ChatPage /></ProtectedRoute>
        } />
        <Route path="/admin" element={
          <ProtectedRoute><AdminPage /></ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  )
}
