import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import { ChatPage } from '@/pages/ChatPage'
import { AdminPage } from '@/pages/AdminPage'
import { LoginPage } from '@/pages/LoginPage'
import { useAuthStore } from '@/store/authStore'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.PROD ? '/tools/exlunofficialchatbot' : '/'}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
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
