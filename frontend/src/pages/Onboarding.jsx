import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import TutorBlob from '../components/ui/TutorBlob.jsx'
import Icon from '../components/ui/Icon.jsx'

const OPCIONES = [
  {
    rol: 'estudiante',
    titulo: 'Soy estudiante',
    desc: 'Quiero conversar con el tutor sobre el material de mis cursos.',
    icon: 'user',
    color: 'mint',
  },
  {
    rol: 'docente',
    titulo: 'Soy docente',
    desc: 'Quiero subir material y ver cómo lo usan mis estudiantes.',
    icon: 'book',
    color: 'lav',
  },
]

export default function Onboarding() {
  const { profile, needsOnboarding, setRol } = useAuth()
  const navigate = useNavigate()
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!needsOnboarding && profile?.rol) {
      navigate('/dashboard', { replace: true })
    }
  }, [needsOnboarding, profile?.rol, navigate])

  if (!needsOnboarding && profile?.rol) return null

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

  const firstName = profile?.nombre?.split(' ')[0]

  return (
    <main style={s.main}>
      <div className="card card-elev" style={s.card}>
        <div style={s.head}>
          <TutorBlob size={56} />
          <div>
            <div className="t-eyebrow" style={{ marginBottom: 6 }}>Bienvenida ·  ProfeTEC.IA</div>
            <h2 style={{ margin: 0 }}>
              Hola{firstName ? <>, <em style={{ fontStyle: 'italic', fontWeight: 500, color: 'var(--amber-700)' }}>{firstName}</em></> : ''}.
            </h2>
            <p className="t-muted" style={{ marginTop: 6 }}>¿Cómo vas a usar el tutor?</p>
          </div>
        </div>

        <div style={s.opciones}>
          {OPCIONES.map((o) => {
            const active = selected === o.rol
            return (
              <button
                key={o.rol}
                type="button"
                onClick={() => setSelected(o.rol)}
                style={{
                  ...s.opcion,
                  borderColor: active ? 'var(--amber-500)' : 'var(--ink-100)',
                  background: active ? 'var(--amber-100)' : 'var(--surface)',
                }}
              >
                <span
                  className={`chip chip-${o.color}`}
                  style={{ alignSelf: 'flex-start', padding: '6px 10px' }}
                >
                  <Icon name={o.icon} size={14} />
                  {o.titulo}
                </span>
                <p style={s.opcionDesc}>{o.desc}</p>
              </button>
            )
          })}
        </div>

        {error && <p style={s.error}>{error}</p>}

        <button
          type="button"
          onClick={handleConfirm}
          disabled={!selected || loading}
          className="btn btn-primary"
          style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}
        >
          {loading ? 'Guardando…' : 'Continuar'}
          <Icon name="arrow" size={15} />
        </button>
      </div>
    </main>
  )
}

const s = {
  main: { minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '32px 16px' },
  card: { width: '100%', maxWidth: 540, padding: '36px 32px' },
  head: { display: 'flex', alignItems: 'center', gap: 16, marginBottom: 28 },
  opciones: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: 12,
    marginBottom: 20,
  },
  opcion: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    padding: '16px 16px 18px',
    border: '1px solid var(--ink-100)',
    borderRadius: 'var(--r-lg)',
    background: 'var(--surface)',
    textAlign: 'left',
    cursor: 'pointer',
    transition: 'border-color .15s ease, background .15s ease',
  },
  opcionDesc: { fontSize: 13, color: 'var(--ink-500)', margin: 0 },
  error: {
    color: 'var(--danger)',
    fontSize: 13,
    marginBottom: 12,
    background: 'rgba(214,90,71,.07)',
    border: '1px solid rgba(214,90,71,.25)',
    borderRadius: 'var(--r-sm)',
    padding: '8px 12px',
  },
}
