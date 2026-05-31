import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { getCursos } from '../api/cursos.js'
import Navbar from '../components/Navbar.jsx'
import TutorBlob from '../components/ui/TutorBlob.jsx'
import Icon from '../components/ui/Icon.jsx'
import SectionHead from '../components/ui/SectionHead.jsx'
import CourseCover, { colorForIndex } from '../components/ui/CourseCover.jsx'

export default function Dashboard() {
  const { profile, firebaseUser } = useAuth()
  const navigate = useNavigate()
  const [cursos, setCursos] = useState([])
  const [loading, setLoading] = useState(true)

  const esDocente = profile?.rol === 'docente'
  const nombre =
    (profile?.nombre || firebaseUser?.displayName || '').split(' ')[0] || 'estudiante'

  useEffect(() => {
    let active = true
    getCursos()
      .then((list) => {
        if (active) setCursos(list)
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const greeting = useGreeting()
  const primerCurso = cursos[0]

  const abrirTutor = () => {
    if (esDocente) {
      navigate(primerCurso ? `/cursos/${primerCurso.id}` : '/cursos')
    } else {
      navigate(primerCurso ? `/chat/${primerCurso.id}` : '/cursos')
    }
  }

  return (
    <>
      <Navbar />
      <main style={s.main}>
        {/* HERO */}
        <section style={s.hero} className="dash-hero">
          <div>
            <div className="t-eyebrow" style={{ marginBottom: 8 }}>{greeting.eyebrow}</div>
            <h1 style={{ marginBottom: 12 }}>
              {greeting.salutation},{' '}
              <em style={{ fontStyle: 'italic', fontWeight: 500, color: 'var(--amber-700)' }}>
                {nombre}
              </em>
              .
            </h1>
            <p style={s.lead}>
              {esDocente
                ? <>Gestiona tus cursos, sube material y deja que <strong style={{ color: 'var(--ink-900)' }}>ProfeTEC.IA</strong> responda con citas verificables a tus estudiantes.</>
                : cursos.length > 0
                  ? <>Tienes <strong style={{ color: 'var(--ink-900)' }}>{cursos.length} curso{cursos.length === 1 ? '' : 's'}</strong> conectado{cursos.length === 1 ? '' : 's'}. Empecemos por una pregunta al tutor.</>
                  : <>Únete a un curso con el código que te dio tu docente y empieza a preguntarle al tutor.</>}
            </p>

            <div style={s.ctas}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={abrirTutor}
                disabled={loading}
              >
                <Icon name="chat" size={15} />
                {esDocente ? 'Ver mis cursos' : 'Abrir tutor'}
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => navigate('/cursos')}
              >
                <Icon name="book" size={15} />
                {esDocente ? 'Material' : 'Mis cursos'}
              </button>
            </div>
          </div>

          <div style={s.mascotWrap}>
            <div style={s.mascotOrb}>
              <TutorBlob size={130} />
            </div>
            <div style={s.statusPill}>
              <span style={s.statusDot} />
              Tutor listo
            </div>
          </div>
        </section>

        {/* COURSES */}
        <SectionHead
          eyebrow={esDocente ? 'Tus cursos' : 'Tus cursos · Ciclo 2026-I'}
          title={esDocente ? 'Mis cursos' : 'Mis cursos'}
          action={
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => navigate('/cursos')}
            >
              <Icon name="plus" size={14} />
              {esDocente ? 'Nuevo curso' : 'Inscribirme'}
            </button>
          }
        />

        {loading ? (
          <p className="t-muted">Cargando cursos…</p>
        ) : cursos.length === 0 ? (
          <div className="card" style={s.emptyCard}>
            <p style={{ marginBottom: 14 }}>
              {esDocente
                ? 'Aún no tienes cursos. Crea uno para empezar a subir material.'
                : 'Aún no estás inscrito en ningún curso. Pídele a tu docente el código del curso.'}
            </p>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => navigate('/cursos')}
            >
              {esDocente ? 'Crear primer curso' : 'Ir a inscribirme'}
            </button>
          </div>
        ) : (
          <div style={s.cursosGrid}>
            {cursos.map((c, i) => (
              <CursoCard
                key={c.id}
                curso={c}
                color={colorForIndex(i)}
                onClick={() =>
                  esDocente
                    ? navigate(`/cursos/${c.id}`)
                    : navigate(`/chat/${c.id}`)
                }
              />
            ))}
          </div>
        )}

        {/* TWO COLUMNS: tips + suggestions */}
        <div style={s.bottomGrid} className="dash-bottom">
          <div>
            <SectionHead
              eyebrow="Sobre el tutor"
              title="Así funciona ProfeTEC.IA"
            />
            <div className="card" style={{ padding: 4 }}>
              {INFO_ROWS.map((row, i) => (
                <div
                  key={row.title}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 14,
                    padding: '14px 14px',
                    borderBottom:
                      i < INFO_ROWS.length - 1 ? '1px solid var(--ink-100)' : 'none',
                  }}
                >
                  <div
                    style={{
                      width: 38,
                      height: 38,
                      borderRadius: 10,
                      display: 'grid',
                      placeItems: 'center',
                      flex: 'none',
                      background:
                        row.color === 'amber'
                          ? 'var(--amber-100)'
                          : row.color === 'mint'
                            ? 'var(--mint-100)'
                            : 'var(--lav-100)',
                      color:
                        row.color === 'amber'
                          ? 'var(--amber-700)'
                          : row.color === 'mint'
                            ? 'var(--mint-700)'
                            : 'var(--lav-700)',
                    }}
                  >
                    <Icon name={row.icon} size={17} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 500, fontSize: 14 }}>{row.title}</div>
                    <div className="t-tiny t-muted" style={{ marginTop: 4, lineHeight: 1.5 }}>
                      {row.desc}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <aside>
            <SectionHead eyebrow="Sugerencias" title="¿Por dónde empiezo?" />
            <div
              className="card"
              style={{
                padding: 18,
                background: 'linear-gradient(160deg, var(--amber-100), var(--surface) 60%)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                <TutorBlob size={42} />
                <div style={{ fontSize: 13, color: 'var(--ink-700)' }}>
                  {esDocente
                    ? 'Sube tu primer PDF y el tutor lo indexará en segundos.'
                    : 'Hazme una pregunta concreta del material y te respondo con la cita.'}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {(esDocente ? SUGG_DOCENTE : SUGG_ESTUDIANTE).map((sg) => (
                  <button
                    key={sg.text}
                    type="button"
                    onClick={() => {
                      if (sg.action === 'cursos') navigate('/cursos')
                      else abrirTutor()
                    }}
                    style={s.suggBtn}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--amber-500)')}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--ink-100)')}
                  >
                    <Icon
                      name={sg.icon}
                      size={15}
                      style={{ color: 'var(--amber-700)', flex: 'none' }}
                    />
                    <span>{sg.text}</span>
                  </button>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </main>

      <style>{`
        @media (max-width: 880px) {
          .dash-hero { grid-template-columns: 1fr !important; }
          .dash-hero > div:last-child { justify-self: center; }
          .dash-bottom { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </>
  )
}

function CursoCard({ curso, color, onClick }) {
  return (
    <article
      className="card"
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
      role="button"
      tabIndex={0}
      style={{
        cursor: 'pointer',
        overflow: 'hidden',
        transition: 'transform .15s ease, box-shadow .15s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)'
        e.currentTarget.style.boxShadow = 'var(--sh-3)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = ''
        e.currentTarget.style.boxShadow = ''
      }}
    >
      <CourseCover variant={color} />
      <div style={{ padding: 18 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
          <span className="t-mono t-tiny" style={{ color: 'var(--ink-500)' }}>
            {curso.codigo}
          </span>
        </div>
        <h3 style={{ marginBottom: 6, lineHeight: 1.2 }}>{curso.nombre}</h3>
        {curso.descripcion && (
          <div
            className="t-tiny t-muted"
            style={{
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              minHeight: 32,
            }}
          >
            {curso.descripcion}
          </div>
        )}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: 18,
            paddingTop: 14,
            borderTop: '1px dashed var(--ink-100)',
          }}
        >
          <span className="t-tiny t-muted">Abrir tutor</span>
          <Icon name="arrow" size={14} style={{ color: 'var(--ink-500)' }} />
        </div>
      </div>
    </article>
  )
}

const INFO_ROWS = [
  {
    icon: 'chat',
    color: 'amber',
    title: 'Conversa con el tutor',
    desc:
      'Pregúntale a ProfeTEC.IA sobre el material de tus cursos. Cada respuesta se ancla en los documentos que tu docente subió.',
  },
  {
    icon: 'file',
    color: 'mint',
    title: 'Citas verificables',
    desc:
      'Junto a cada respuesta verás las fuentes consultadas, con el fragmento exacto y la página del documento.',
  },
  {
    icon: 'sparkle',
    color: 'lav',
    title: 'Privado por curso',
    desc:
      'Solo accedes al material de los cursos en los que estás inscrito. Tu conversación es solo tuya.',
  },
]

const SUGG_ESTUDIANTE = [
  { icon: 'sparkle', text: 'Pregúntale al tutor un concepto difícil de tu última clase', action: 'chat' },
  { icon: 'file',    text: 'Pide un resumen de la sesión anterior con citas',           action: 'chat' },
  { icon: 'target',  text: 'Únete a otro curso con su código',                          action: 'cursos' },
]
const SUGG_DOCENTE = [
  { icon: 'sparkle', text: 'Sube tu primer PDF o slide y deja que el tutor lo indexe', action: 'cursos' },
  { icon: 'file',    text: 'Revisa qué documentos han sido más consultados',           action: 'cursos' },
  { icon: 'target',  text: 'Comparte el código del curso con tus estudiantes',         action: 'cursos' },
]

function useGreeting() {
  const d = new Date()
  const h = d.getHours()
  const fecha = d.toLocaleDateString('es-PE', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
  })
  let salutation
  if (h < 12) salutation = 'Buenos días'
  else if (h < 19) salutation = 'Buenas tardes'
  else salutation = 'Buenas noches'
  return { eyebrow: `${salutation} · ${fecha}`, salutation }
}

const s = {
  main: { maxWidth: 'var(--maxw)', margin: '0 auto', padding: '32px 24px 80px' },
  hero: {
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    alignItems: 'center',
    gap: 24,
    marginBottom: 40,
  },
  lead: { fontSize: 17, color: 'var(--ink-500)', maxWidth: 580 },
  ctas: { display: 'flex', gap: 10, marginTop: 22, flexWrap: 'wrap' },
  mascotWrap: { position: 'relative' },
  mascotOrb: {
    width: 220,
    height: 220,
    background:
      'radial-gradient(circle at 30% 30%, var(--amber-100), var(--amber-200) 70%)',
    borderRadius: '50%',
    display: 'grid',
    placeItems: 'center',
    boxShadow: 'var(--sh-2)',
  },
  statusPill: {
    position: 'absolute',
    top: 14,
    right: -10,
    background: 'var(--surface)',
    padding: '8px 12px',
    borderRadius: 'var(--r-pill)',
    boxShadow: 'var(--sh-2)',
    fontSize: 13,
    fontWeight: 500,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    color: 'var(--ink-900)',
  },
  statusDot: { width: 7, height: 7, background: 'var(--mint-500)', borderRadius: '50%' },
  cursosGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: 18,
    marginBottom: 48,
  },
  emptyCard: {
    padding: 28,
    textAlign: 'center',
    marginBottom: 48,
    color: 'var(--ink-700)',
  },
  bottomGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 360px',
    gap: 24,
  },
  suggBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    textAlign: 'left',
    padding: '10px 12px',
    background: 'var(--surface)',
    border: '1px solid var(--ink-100)',
    borderRadius: 'var(--r-md)',
    fontSize: 13,
    color: 'var(--ink-900)',
    cursor: 'pointer',
    transition: 'border-color .15s ease',
  },
}
