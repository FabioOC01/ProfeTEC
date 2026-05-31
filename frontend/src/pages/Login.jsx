import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Login() {
  const { firebaseUser, profile, needsOnboarding, loginWithGoogle } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  // Redirige cuando Firebase confirma la sesión (evita la race contra RequireAuth).
  useEffect(() => {
    if (!firebaseUser) return
    const from = location.state?.from?.pathname
    if (needsOnboarding || !profile?.rol) {
      navigate('/onboarding', { replace: true })
    } else {
      navigate(from && from !== '/login' ? from : '/dashboard', { replace: true })
    }
  }, [firebaseUser, profile?.rol, needsOnboarding, navigate, location.state])

  const handleGoogle = async () => {
    setError(null)
    setLoading(true)
    try {
      await loginWithGoogle()
      // No navegamos aquí: el efecto de arriba lo hará cuando el contexto refleje la sesión.
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  return (
    <div style={s.grid} className="login-grid">
      {/* Left: brand panel */}
      <div style={s.brand} className="login-brand">
        <div style={s.orbTop} />
        <div style={s.orbBottom} />

        <div style={s.brandHeader}>
          <img
            src="/logo.png"
            alt="ProfeTEC"
            style={{
              width: 46,
              height: 46,
              objectFit: 'contain',
              display: 'block',
            }}
          />
          <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1 }}>
            <span style={s.brandWordmark}>ProfeTEC</span>
            <span style={s.brandSub}>TECSUP</span>
          </div>
        </div>

        <div style={s.brandBody}>
          <div className="t-eyebrow" style={{ color: 'rgba(255,255,255,.7)', marginBottom: 14 }}>
            Tu compañero de estudio
          </div>
          <h1 style={s.brandH1}>
            Pregúntale lo que sea sobre{' '}
            <em style={{ fontStyle: 'italic', fontWeight: 500 }}>tu</em> curso.
          </h1>
          <p style={s.brandLead}>
            Respuestas con citas verificables del material que tus docentes ya
            subieron. Quizzes que se ajustan a lo que estás aprendiendo. Sin
            alucinaciones.
          </p>

          <div style={s.stats}>
            <Stat n="14" label="cursos" />
            <Stat n="2.3k" label="preguntas resueltas" />
            <Stat n="96%" label="con cita" />
          </div>
        </div>
      </div>

      {/* Right: sign-in */}
      <div style={s.signWrap}>
        <div style={s.signCard}>
          <h2 style={{ marginBottom: 8 }}>Iniciar sesión</h2>
          <p className="t-muted" style={{ marginBottom: 28 }}>
            Usa tu correo institucional{' '}
          </p>

          <button
            type="button"
            onClick={handleGoogle}
            disabled={loading}
            style={{ ...s.googleBtn, opacity: loading ? 0.7 : 1 }}
          >
            <GoogleG />
            <span>{loading ? 'Conectando…' : 'Continuar con Google'}</span>
          </button>

          {error && (
            <p style={s.error}>
              {error}
            </p>
          )}

          <div style={s.divider}>
            <div style={s.dividerLine} />
            <span style={s.dividerWord}>o</span>
            <div style={s.dividerLine} />
          </div>

          <label className="field-label" htmlFor="login-email">
            Correo institucional
          </label>
          <input
            id="login-email"
            className="field-input"
            type="email"
            placeholder="@tecsup.edu.pe"
            disabled
            title="Próximamente"
          />
          <button
            type="button"
            className="btn btn-primary"
            disabled
            title="Próximamente"
            style={{ width: '100%', justifyContent: 'center', marginTop: 12 }}
          >
            Enviar enlace mágico
          </button>

          <p className="t-faint t-tiny" style={{ marginTop: 24, textAlign: 'center' }}>
            Al continuar aceptas los términos de uso y la política de privacidad de TECSUP.
          </p>
        </div>
      </div>

      <style>{`
        @media (max-width: 880px) {
          .login-grid { grid-template-columns: 1fr !important; }
          .login-grid > .login-brand { display: none; }
        }
      `}</style>
    </div>
  )
}

function Stat({ n, label }) {
  return (
    <div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 26, color: 'white' }}>{n}</div>
      <div style={{ fontSize: 13, color: 'rgba(255,255,255,.78)' }}>{label}</div>
    </div>
  )
}

function GoogleG() {
  return (
    <svg width="20" height="20" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92a8.78 8.78 0 0 0 2.68-6.62z" />
      <path fill="#34A853" d="M9 18a8.6 8.6 0 0 0 5.96-2.18l-2.92-2.26a5.4 5.4 0 0 1-8.04-2.83H.95v2.33A9 9 0 0 0 9 18z" />
      <path fill="#FBBC05" d="M4 10.73a5.4 5.4 0 0 1 0-3.46V4.94H.95a9 9 0 0 0 0 8.12L4 10.73z" />
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58A8.6 8.6 0 0 0 9 0 9 9 0 0 0 .95 4.94L4 7.27A5.36 5.36 0 0 1 9 3.58z" />
    </svg>
  )
}

const s = {
  grid: {
    minHeight: '100vh',
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
  },
  brand: {
    background:
      'linear-gradient(140deg, var(--amber-500), var(--amber-700) 55%, #0a1a2e)',
    padding: 48,
    position: 'relative',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    color: 'white',
  },
  orbTop: {
    position: 'absolute',
    top: -80,
    right: -60,
    width: 320,
    height: 320,
    background: 'radial-gradient(circle, rgba(255,255,255,.18), transparent 60%)',
    borderRadius: '50%',
    pointerEvents: 'none',
  },
  orbBottom: {
    position: 'absolute',
    bottom: -120,
    left: -100,
    width: 400,
    height: 400,
    background: 'radial-gradient(circle, var(--amber-300), transparent 60%)',
    opacity: 0.28,
    borderRadius: '50%',
    pointerEvents: 'none',
  },
  brandHeader: { display: 'flex', alignItems: 'center', gap: 10, position: 'relative', zIndex: 1 },
  brandWordmark: {
    fontFamily: 'var(--font-display)',
    fontWeight: 600,
    fontSize: 22,
    color: 'white',
  },
  brandSub: {
    fontFamily: 'var(--font-mono)',
    fontSize: 10,
    opacity: 0.7,
    letterSpacing: '.18em',
    marginTop: 4,
  },
  brandBody: { marginTop: 'auto', position: 'relative', maxWidth: 460, zIndex: 1 },
  brandH1: {
    color: 'white',
    fontSize: 'clamp(34px, 4.2vw, 52px)',
    lineHeight: 1.05,
    marginBottom: 18,
  },
  brandLead: {
    color: 'rgba(255,255,255,.82)',
    fontSize: 17,
    lineHeight: 1.5,
  },
  stats: {
    display: 'flex',
    gap: 24,
    marginTop: 32,
  },
  signWrap: {
    padding: 48,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#ffffff',
  },
  signCard: { width: '100%', maxWidth: 380 },
  googleBtn: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    padding: '14px 18px',
    background: 'var(--surface)',
    border: '1px solid var(--ink-200)',
    borderRadius: 14,
    fontSize: 15,
    fontWeight: 500,
    boxShadow: 'var(--sh-1)',
    cursor: 'pointer',
    color: 'var(--ink-900)',
    transition: 'transform .12s ease, box-shadow .15s ease',
  },
  divider: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    margin: '20px 0',
    color: 'var(--ink-400)',
    fontSize: 12,
  },
  dividerLine: { flex: 1, height: 1, background: 'var(--ink-100)' },
  dividerWord: { fontFamily: 'var(--font-mono)' },
  error: {
    color: 'var(--danger)',
    fontSize: 13,
    marginTop: 12,
    background: 'rgba(214,90,71,.07)',
    border: '1px solid rgba(214,90,71,.25)',
    borderRadius: 'var(--r-sm)',
    padding: '8px 12px',
  },
}
