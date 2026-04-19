import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

const OPCIONES = [
  {
    rol: 'docente',
    titulo: 'Soy docente',
    desc: 'Subo material de estudio y gestiono cursos.',
    icon: '👨‍🏫',
  },
  {
    rol: 'estudiante',
    titulo: 'Soy estudiante',
    desc: 'Consulto al tutor y respondo quizzes.',
    icon: '👨‍🎓',
  },
]

export default function Onboarding() {
  const { profile, needsOnboarding, setRol } = useAuth()
  const navigate = useNavigate()
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Si ya tiene rol, saltar al dashboard directamente
  if (!needsOnboarding && profile?.rol) {
    navigate('/dashboard', { replace: true })
    return null
  }

  const handleConfirm = async () => {
    if (!selected) return
    setLoading(true)
    setError(null)
    try {
      await setRol(selected)
      navigate('/dashboard', { replace: true })
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={s.main}>
      <div style={s.card}>
        <h2 style={s.title}>Bienvenido{profile?.nombre ? `, ${profile.nombre.split(' ')[0]}` : ''}.</h2>
        <p style={s.sub}>¿Cómo usarás ProfeTEC.IA?</p>

        <div style={s.opciones}>
          {OPCIONES.map((o) => (
            <button
              key={o.rol}
              style={{ ...s.opcion, ...(selected === o.rol ? s.opcionActiva : {}) }}
              onClick={() => setSelected(o.rol)}
            >
              <span style={s.icon}>{o.icon}</span>
              <strong>{o.titulo}</strong>
              <span style={s.desc}>{o.desc}</span>
            </button>
          ))}
        </div>

        {error && <p style={s.error}>{error}</p>}

        <button
          onClick={handleConfirm}
          disabled={!selected || loading}
          style={{ ...s.btn, opacity: !selected || loading ? 0.5 : 1 }}
        >
          {loading ? 'Guardando…' : 'Continuar →'}
        </button>
      </div>
    </main>
  )
}

const s = {
  main: { minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '1rem' },
  card: {
    width: '100%', maxWidth: 480, background: 'var(--card)',
    border: '1px solid var(--border)', borderRadius: 12, padding: '2.5rem 2rem',
    boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
  },
  title: { margin: 0, fontSize: '1.5rem' },
  sub: { color: 'var(--text-dim)', marginTop: '0.5rem', marginBottom: '2rem' },
  opciones: { display: 'flex', gap: '1rem', marginBottom: '1.5rem' },
  opcion: {
    flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
    gap: '0.5rem', padding: '1.25rem 1rem', border: '2px solid var(--border)',
    borderRadius: 10, cursor: 'pointer', background: 'transparent',
    color: 'var(--text)', transition: 'border-color 0.15s, background 0.15s',
  },
  opcionActiva: { borderColor: '#2f81f7', background: 'rgba(47,129,247,0.1)' },
  icon: { fontSize: '2rem' },
  desc: { fontSize: '0.8rem', color: 'var(--text-dim)', textAlign: 'center' },
  btn: {
    width: '100%', padding: '0.75rem', fontSize: '1rem',
    background: '#2f81f7', color: '#fff', border: 'none',
    borderRadius: 8, cursor: 'pointer', fontWeight: 600,
  },
  error: { color: 'var(--error)', fontSize: '0.875rem', marginBottom: '1rem' },
}
