import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import Navbar from '../components/Navbar.jsx'

export default function Dashboard() {
  const { profile, firebaseUser } = useAuth()
  const navigate = useNavigate()

  const esDocente = profile?.rol === 'docente'
  const nombre = (profile?.nombre || firebaseUser?.displayName || '').split(' ')[0]

  return (
    <>
      <Navbar />
      <main style={s.main}>
        <section style={s.hero}>
          <h1 style={s.titulo}>
            Hola{nombre ? `, ${nombre}` : ''} 
          </h1>
          <p style={s.subtitulo}>
            {esDocente
              ? 'Gestiona tus cursos, sube material y deja que ProfeTEC.IA responda a tus estudiantes.'
              : 'Explora tus cursos y consulta al tutor virtual sobre cualquier duda del material.'}
          </p>
        </section>

        <section>
          <h2 style={s.h2}>Acciones rápidas</h2>
          <div style={s.grid}>
            <ActionCard
              icon=""
              titulo={esDocente ? 'Mis cursos' : 'Cursos disponibles'}
              desc={
                esDocente
                  ? 'Crea, edita y gestiona tus cursos y material.'
                  : 'Explora los cursos y empieza a chatear con el tutor.'
              }
              onClick={() => navigate('/cursos')}
            />

            <ActionCard
              icon=""
              titulo="Chat con el tutor"
              desc="Abre un curso y conversa con ProfeTEC.IA sobre el material."
              onClick={() => navigate('/cursos')}
            />

            <ActionCard
              icon=""
              titulo="Quizzes"
              desc="Genera y responde evaluaciones automáticas."
              onClick={() => {}}
              disabled
              badge=""
            />

            <ActionCard
              icon=""
              titulo="Panel docente"
              desc="Métricas de uso, preguntas frecuentes y feedback."
              onClick={() => {}}
              disabled
              badge=""
            />
          </div>
        </section>

        <section style={s.infoSection}>
          <div style={s.infoCard}>
            <h3 style={s.infoTitulo}> Sobre ProfeTEC.IA</h3>
            <p style={s.infoTexto}>
              Tutor virtual con inteligencia artificial construido sobre Vertex AI
              (Gemini 2.5 Flash) + RAG. Las respuestas se basan únicamente en el
              material subido por tus docentes, con citas al documento fuente.
            </p>
          </div>
          <div style={s.infoCard}>
            <h3 style={s.infoTitulo}>Tu privacidad</h3>
            <p style={s.infoTexto}>
              Solo accedes al material de los cursos permitidos. Tus conversaciones
              son privadas y únicamente tú puedes verlas en tu historial.
            </p>
          </div>
        </section>
      </main>
    </>
  )
}

function ActionCard({ icon, titulo, desc, onClick, disabled = false, badge }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{ ...s.card, opacity: disabled ? 0.45 : 1, cursor: disabled ? 'not-allowed' : 'pointer' }}
    >
      <span style={s.cardIcon}>{icon}</span>
      <div style={{ flex: 1 }}>
        <div style={s.cardHeader}>
          <strong style={s.cardTitulo}>{titulo}</strong>
          {badge && <span style={s.badge}>{badge}</span>}
        </div>
        <p style={s.cardDesc}>{desc}</p>
      </div>
      {!disabled && <span style={s.cardArrow}>→</span>}
    </button>
  )
}

const s = {
  main: { maxWidth: 1100, margin: '0 auto', padding: '2rem 1.5rem' },
  hero: { marginBottom: '2.5rem' },
  titulo: { margin: 0, fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.02em' },
  subtitulo: { color: 'var(--text-dim)', margin: '0.5rem 0 0', fontSize: '1rem', maxWidth: 640 },
  h2: { fontSize: '0.85rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 1rem' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '1rem' },
  card: {
    display: 'flex', alignItems: 'flex-start', gap: '0.9rem',
    background: 'var(--card)', border: '1px solid var(--border)',
    borderRadius: 12, padding: '1.25rem', textAlign: 'left',
    color: 'var(--text)', transition: 'border-color 0.2s, transform 0.1s, background 0.2s',
  },
  cardIcon: { fontSize: '1.75rem', flexShrink: 0 },
  cardHeader: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem', flexWrap: 'wrap' },
  cardTitulo: { fontSize: '0.95rem' },
  cardDesc: { margin: 0, fontSize: '0.825rem', color: 'var(--text-dim)', lineHeight: 1.45 },
  cardArrow: { color: 'var(--text-dim)', fontSize: '1.2rem', alignSelf: 'center', transition: 'transform 0.15s' },
  badge: {
    fontSize: '0.65rem', background: 'var(--border)', color: 'var(--text-dim)',
    padding: '0.15rem 0.5rem', borderRadius: 99, fontWeight: 500, letterSpacing: '0.02em',
  },
  infoSection: {
    marginTop: '3rem',
    display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem',
  },
  infoCard: {
    background: 'var(--card)', border: '1px solid var(--border)',
    borderRadius: 12, padding: '1.25rem',
  },
  infoTitulo: { margin: '0 0 0.5rem', fontSize: '0.95rem' },
  infoTexto: { margin: 0, fontSize: '0.825rem', color: 'var(--text-dim)', lineHeight: 1.55 },
}
