import { useState } from 'react'
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import { ChatPage } from '@/pages/ChatPage'
import { AdminPage } from '@/pages/AdminPage'
import { AboutPage } from '@/pages/AboutPage'
import { LoginPage } from '@/pages/LoginPage'
import { OAuthCallback } from '@/pages/OAuthCallback'
import { TermsModal } from '@/components/TermsModal'
import { useAuthStore } from '@/store/authStore'
import { usePageView } from '@/analytics'
import { useTheme } from '@/hooks/useTheme'

const TERMS_KEY = 'rovr_terms_accepted'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

/** Render-null component that fires page_view on every route change. */
function RouterAnalytics() {
  usePageView()
  return null
}

/**
 * Shows the terms modal once per browser after the first successful login.
 * Renders on top of everything; the backdrop blocks all interaction behind it.
 */
function TermsGate() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const [accepted, setAccepted] = useState(
    () => localStorage.getItem(TERMS_KEY) === 'true'
  )

  if (!isAuthenticated || accepted) return null
  return <TermsModal onAccept={() => setAccepted(true)} />
}

export default function App() {
  useTheme()

  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '') || '/'}>
      <div className="w-full min-h-screen flex flex-col">
        <RouterAnalytics />
        <TermsGate />
        <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/callback" element={<OAuthCallback />} />
        <Route path="/" element={
          <ProtectedRoute><ChatPage /></ProtectedRoute>
        } />
        <Route path="/about" element={
          <ProtectedRoute><AboutPage /></ProtectedRoute>
        } />
        <Route path="/admin" element={
          <ProtectedRoute><AdminPage /></ProtectedRoute>
        } />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
