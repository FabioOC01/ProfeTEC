import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function RequireAuth({ children }) {
  const { firebaseUser, loading } = useAuth()
  const location = useLocation()

  if (loading) return <div style={styles.loading}>Cargando…</div>
  if (!firebaseUser) return <Navigate to="/login" state={{ from: location }} replace />
  return children
}

const styles = {
  loading: {
    display: 'grid',
    placeItems: 'center',
    height: '100vh',
    color: 'var(--text-dim)',
    fontSize: '1rem',
  },
}
