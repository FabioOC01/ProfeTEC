import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getCurso } from '../../api/cursos.js'
import { crearQuiz, eliminarQuiz, listarQuizzes } from '../../api/quizzes.js'
import { useAuth } from '../../context/AuthContext.jsx'
import Navbar from '../../components/Navbar.jsx'
import Icon from '../../components/ui/Icon.jsx'

export default function QuizzesPage() {
  const { cursoId } = useParams()
  const navigate = useNavigate()
  const { profile } = useAuth()
  const isDocente = profile?.rol === 'docente'

  const [curso, setCurso] = useState(null)
  const [quizzes, setQuizzes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [crearOpen, setCrearOpen] = useState(false)
  const [creando, setCreando] = useState(false)
  const [form, setForm] = useState({
    titulo: '',
    tema: '',
    num_preguntas: 5,
    semana_desde: '',
    semana_hasta: '',
  })

  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([getCurso(cursoId), listarQuizzes(cursoId)])
      .then(([c, qs]) => {
        if (!alive) return
        setCurso(c)
        setQuizzes(qs)
      })
      .catch((e) => alive && setError(e.response?.data?.detail || e.message))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [cursoId])

  const onCrear = async (e) => {
    e.preventDefault()
    if (!form.titulo.trim()) return
    setCreando(true)
    setError(null)
    try {
      const payload = {
        ...form,
        semana_desde: form.semana_desde ? Number(form.semana_desde) : null,
        semana_hasta: form.semana_hasta ? Number(form.semana_hasta) : null,
      }
      const nuevo = await crearQuiz(cursoId, payload)
      setQuizzes((prev) => [
        {
          id: nuevo.id,
          titulo: nuevo.titulo,
          tema: nuevo.tema,
          semana_desde: nuevo.semana_desde,
          semana_hasta: nuevo.semana_hasta,
          num_preguntas: nuevo.preguntas.length,
          creado_en: nuevo.creado_en,
        },
        ...prev,
      ])
      setForm({ titulo: '', tema: '', num_preguntas: 5, semana_desde: '', semana_hasta: '' })
      setCrearOpen(false)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setCreando(false)
    }
  }

  const onEliminar = async (quizId) => {
    if (!confirm('¿Eliminar este quiz? Esta acción no se puede deshacer.')) return
    try {
      await eliminarQuiz(cursoId, quizId)
      setQuizzes((prev) => prev.filter((q) => q.id !== quizId))
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    }
  }

  return (
    <>
      <Navbar />
      <div style={s.shell}>
        <header style={s.header}>
          <div>
            <div className="t-eyebrow" style={{ color: 'var(--lav-700)' }}>Quizzes</div>
            <h1 style={{ fontSize: 24, margin: '4px 0 4px' }}>
              {curso?.nombre || 'Curso'}
            </h1>
            <p className="t-tiny t-muted">
              {isDocente
                ? 'Genera y administra cuestionarios a partir del material del curso.'
                : 'Resuelve cuestionarios generados a partir del material del curso.'}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={() => navigate(isDocente ? `/cursos/${cursoId}` : `/chat/${cursoId}`)}
              className="btn btn-ghost"
            >
              <Icon name="chevron" size={14} style={{ transform: 'rotate(180deg)' }} /> Volver
            </button>
            {isDocente && (
              <button
                type="button"
                onClick={() => setCrearOpen((v) => !v)}
                className="btn btn-primary"
              >
                <Icon name="sparkle" size={14} /> Nuevo quiz
              </button>
            )}
          </div>
        </header>

        {error && <p style={s.error}><Icon name="x" size={14} /> {error}</p>}

        {isDocente && crearOpen && (
          <form onSubmit={onCrear} style={s.card}>
            <h3 style={{ marginBottom: 12 }}>Generar nuevo quiz</h3>
            <label style={s.label}>
              <span>Título</span>
              <input
                type="text"
                value={form.titulo}
                onChange={(e) => setForm({ ...form, titulo: e.target.value })}
                placeholder="Ej. Repaso de árboles binarios"
                style={s.input}
                maxLength={120}
                required
              />
            </label>
            <label style={s.label}>
              <span>Tema (opcional)</span>
              <input
                type="text"
                value={form.tema}
                onChange={(e) => setForm({ ...form, tema: e.target.value })}
                placeholder="Si lo dejas vacío, se cubrirá el material en general"
                style={s.input}
                maxLength={300}
              />
            </label>
            <label style={s.label}>
              <span>Cantidad de preguntas</span>
              <input
                type="number"
                value={form.num_preguntas}
                onChange={(e) => setForm({ ...form, num_preguntas: Number(e.target.value) })}
                min={3}
                max={10}
                style={s.input}
              />
            </label>
            <div style={s.weekRow}>
              <label style={s.label}>
                <span>Desde semana</span>
                <input
                  type="number"
                  value={form.semana_desde}
                  onChange={(e) => setForm({ ...form, semana_desde: e.target.value })}
                  min={1}
                  max={30}
                  style={s.input}
                  placeholder="Opcional"
                />
              </label>
              <label style={s.label}>
                <span>Hasta semana</span>
                <input
                  type="number"
                  value={form.semana_hasta}
                  onChange={(e) => setForm({ ...form, semana_hasta: e.target.value })}
                  min={1}
                  max={30}
                  style={s.input}
                  placeholder="Opcional"
                />
              </label>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button type="submit" className="btn btn-primary" disabled={creando}>
                {creando ? 'Generando…' : 'Generar quiz'}
              </button>
              <button
                type="button"
                onClick={() => setCrearOpen(false)}
                className="btn btn-ghost"
                disabled={creando}
              >
                Cancelar
              </button>
            </div>
            <p className="t-tiny t-muted" style={{ marginTop: 10 }}>
              La generación puede tardar unos segundos. Las preguntas se basan exclusivamente
              en los documentos cargados al curso.
            </p>
          </form>
        )}

        {loading ? (
          <p className="t-muted" style={{ textAlign: 'center', padding: 40 }}>
            Cargando quizzes…
          </p>
        ) : quizzes.length === 0 ? (
          <div style={s.empty}>
            <p>Aún no hay quizzes en este curso.</p>
            {isDocente && (
              <p className="t-tiny t-muted">
                Sube material al curso y haz clic en <b>Nuevo quiz</b> para generar el primero.
              </p>
            )}
          </div>
        ) : (
          <ul style={s.list}>
            {quizzes.map((q) => (
              <li key={q.id} style={s.item}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Link to={`/cursos/${cursoId}/quizzes/${q.id}`} style={s.itemTitle}>
                    {q.titulo}
                  </Link>
                  <div className="t-tiny t-muted" style={{ marginTop: 4 }}>
                    {q.num_preguntas} preguntas
                    {q.semana_desde && (
                      <>
                        {' '}· Semana {q.semana_desde}
                        {q.semana_hasta && q.semana_hasta !== q.semana_desde
                          ? ` a ${q.semana_hasta}`
                          : ''}
                      </>
                    )}
                    {q.tema && <> · {q.tema}</>}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Link
                    to={`/cursos/${cursoId}/quizzes/${q.id}`}
                    className="btn btn-ghost"
                    style={{ fontSize: 12.5 }}
                  >
                    {isDocente ? 'Ver' : 'Resolver'}
                  </Link>
                  {isDocente && (
                    <button
                      type="button"
                      onClick={() => onEliminar(q.id)}
                      className="btn btn-ghost"
                      title="Eliminar"
                      style={{ color: 'var(--danger)' }}
                    >
                      <Icon name="trash" size={14} />
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
}

const s = {
  shell: {
    maxWidth: 'var(--maxw)',
    margin: '0 auto',
    padding: '20px 18px 60px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 18,
    flexWrap: 'wrap',
  },
  card: {
    background: 'var(--surface)',
    border: '1px solid var(--ink-100)',
    borderRadius: 14,
    padding: 18,
    marginBottom: 18,
    boxShadow: 'var(--sh-1)',
  },
  label: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    fontSize: 13,
    marginBottom: 10,
    color: 'var(--ink-700)',
  },
  input: {
    padding: '9px 12px',
    border: '1px solid var(--ink-100)',
    borderRadius: 10,
    fontSize: 14,
    fontFamily: 'inherit',
    background: 'var(--paper-2)',
    color: 'var(--ink-900)',
    outline: 'none',
  },
  weekRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
    gap: 10,
  },
  list: {
    listStyle: 'none',
    margin: 0,
    padding: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '14px 16px',
    background: 'var(--surface)',
    border: '1px solid var(--ink-100)',
    borderRadius: 12,
  },
  itemTitle: {
    color: 'var(--ink-900)',
    fontWeight: 500,
    fontSize: 15,
    textDecoration: 'none',
  },
  empty: {
    padding: 30,
    textAlign: 'center',
    color: 'var(--ink-500)',
    background: 'var(--paper-2)',
    borderRadius: 12,
    border: '1px dashed var(--ink-100)',
  },
  error: {
    color: 'var(--danger)',
    background: 'rgba(214,90,71,.07)',
    border: '1px solid rgba(214,90,71,.25)',
    borderRadius: 'var(--r-sm)',
    padding: '8px 12px',
    fontSize: 13,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    marginBottom: 12,
  },
}
