import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Dashboard() {
  const { profile, firebaseUser, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const esDocente = profile?.rol === 'docente'

  return (
    <main style={s.main}>
      <header style={s.header}>
        <h1 style={s.logo}>ProfeTEC.IA</h1>
        <div style={s.user}>
          {firebaseUser?.photoURL && (
            <img src={firebaseUser.photoURL} alt="avatar" style={s.avatar} />
          )}
          <span style={s.nombre}>{profile?.nombre || firebaseUser?.displayName}</span>
          <span style={s.rol}>{profile?.rol}</span>
          <button onClick={handleLogout} style={s.btnLogout}>Salir</button>
        </div>
      </header>

      <section style={s.bienvenida}>
        <h2 style={s.h2}>Bienvenido de vuelta</h2>
        <p style={s.p}>
          {esDocente
            ? 'Gestiona tus cursos y sube material para que tus estudiantes puedan consultarlo.'
            : 'Consulta el tutor inteligente sobre el material de tus cursos.'}
        </p>
      </section>

      <div style={s.acciones}>
        {esDocente && (
          <ActionCard
            icon="📚"
            titulo="Mis cursos"
            desc="Crear, editar y gestionar tus cursos."
            onClick={() => navigate('/cursos')}
          />
        )}
        <ActionCard
          icon="💬"
          titulo="Chat con el tutor"
          desc="Consulta al asistente IA sobre el material."
          onClick={() => navigate('/chat')}
          disabled
          badge="Sprint 3"
        />
        <ActionCard
          icon="📝"
          titulo="Quizzes"
          desc="Genera y responde evaluaciones automáticas."
          onClick={() => {}}
          disabled
          badge="Sprint 6"
        />
      </div>
    </main>
  )
}

function ActionCard({ icon, titulo, desc, onClick, disabled = false, badge }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{ ...s.card, opacity: disabled ? 0.5 : 1 }}>
      <span style={s.cardIcon}>{icon}</span>
      <div>
        <strong style={s.cardTitulo}>{titulo}</strong>
        {badge && <span style={s.badge}>{badge}</span>}
        <p style={s.cardDesc}>{desc}</p>
      </div>
    </button>
  )
}

const s = {
  main: { minHeight: '100vh', padding: '1.5rem', maxWidth: 900, margin: '0 auto' },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '0 0 1.5rem', borderBottom: '1px solid var(--border)', marginBottom: '2rem',
  },
  logo: { margin: 0, fontSize: '1.25rem' },
  user: { display: 'flex', alignItems: 'center', gap: '0.75rem' },
  avatar: { width: 32, height: 32, borderRadius: '50%' },
  nombre: { fontSize: '0.9rem' },
  rol: {
    fontSize: '0.75rem', background: '#2f81f720', color: '#2f81f7',
    padding: '0.2rem 0.5rem', borderRadius: 4, textTransform: 'capitalize',
  },
  btnLogout: { fontSize: '0.8rem', padding: '0.3rem 0.75rem', borderRadius: 6 },
  bienvenida: { marginBottom: '2rem' },
  h2: { margin: '0 0 0.5rem' },
  p: { color: 'var(--text-dim)', margin: 0 },
  acciones: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '1rem' },
  card: {
    display: 'flex', flexDirection: 'column', gap: '0.75rem',
    background: 'var(--card)', border: '1px solid var(--border)',
    borderRadius: 10, padding: '1.5rem', textAlign: 'left',
    cursor: 'pointer', transition: 'border-color 0.15s', color: 'var(--text)',
  },
  cardIcon: { fontSize: '1.75rem' },
  cardTitulo: { display: 'block', marginBottom: '0.25rem' },
  cardDesc: { margin: 0, fontSize: '0.8rem', color: 'var(--text-dim)' },
  badge: {
    marginLeft: '0.5rem', fontSize: '0.65rem', background: 'var(--border)',
    color: 'var(--text-dim)', padding: '0.1rem 0.4rem', borderRadius: 4,
  },
}
