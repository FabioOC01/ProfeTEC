import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from './context/AuthContext.jsx'
import RequireAuth from './components/RequireAuth.jsx'

import Login from './pages/Login.jsx'
import Onboarding from './pages/Onboarding.jsx'
import Dashboard from './pages/Dashboard.jsx'
import CursosList from './pages/cursos/CursosList.jsx'
import CursoDetalle from './pages/cursos/CursoDetalle.jsx'

import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route path="/onboarding" element={
            <RequireAuth><Onboarding /></RequireAuth>
          } />

          <Route path="/dashboard" element={
            <RequireAuth><Dashboard /></RequireAuth>
          } />

          <Route path="/cursos" element={
            <RequireAuth><CursosList /></RequireAuth>
          } />

          <Route path="/cursos/:cursoId" element={
            <RequireAuth><CursoDetalle /></RequireAuth>
          } />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
