import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Login() {
  const { loginWithGoogle } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleGoogle = async () => {
    setError(null)
    setLoading(true)
    try {
      await loginWithGoogle()
      navigate('/onboarding')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={s.main}>
      <div style={s.card}>
        <h1 style={s.title}>ProfeTEC.IA</h1>
        <p style={s.sub}>Tutor virtual inteligente para estudiantes de TECSUP</p>

        <button onClick={handleGoogle} disabled={loading} style={s.btn}>
          {loading ? 'Ingresando…' : '▶ Continuar con Google'}
        </button>

        {error && <p style={s.error}>{error}</p>}

        <p style={s.note}>
          Usa tu cuenta institucional <code>@tecsup.edu.pe</code>
        </p>
      </div>
    </main>
  )
}

const s = {
  main: { minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '1rem' },
  card: {
    width: '100%', maxWidth: 420, background: 'var(--card)',
    border: '1px solid var(--border)', borderRadius: 12,
    padding: '2.5rem 2rem', textAlign: 'center',
    boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
  },
  title: { margin: 0, fontSize: '2rem', letterSpacing: '-0.02em' },
  sub: { color: 'var(--text-dim)', marginTop: '0.5rem', marginBottom: '2rem' },
  btn: {
    width: '100%', padding: '0.75rem', fontSize: '1rem',
    background: '#2f81f7', color: '#fff', border: 'none',
    borderRadius: 8, cursor: 'pointer', fontWeight: 600,
    transition: 'opacity 0.15s',
  },
  error: { color: 'var(--error)', fontSize: '0.875rem', marginTop: '1rem' },
  note: { color: 'var(--text-dim)', fontSize: '0.8rem', marginTop: '1.5rem' },
}
