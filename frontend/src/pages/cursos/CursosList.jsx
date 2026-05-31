import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getCursos,
  createCurso,
  inscribirCurso,
  updateCurso,
  deleteCurso,
} from '../../api/cursos.js'
import { useAuth } from '../../context/AuthContext.jsx'
import Navbar from '../../components/Navbar.jsx'
import Icon from '../../components/ui/Icon.jsx'
import SectionHead from '../../components/ui/SectionHead.jsx'
import CourseCover, { colorForIndex } from '../../components/ui/CourseCover.jsx'

export default function CursosList() {
  const navigate = useNavigate()
  const { profile } = useAuth()
  const isDocente = profile?.rol === 'docente'

  const [cursos, setCursos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modal, setModal] = useState(null) // null | 'crear' | curso (editar)
  const [form, setForm] = useState({ nombre: '', descripcion: '' })
  const [codigo, setCodigo] = useState('')
  const [saving, setSaving] = useState(false)

  const cargar = async () => {
    setLoading(true)
    setError(null)
    try {
      setCursos(await getCursos())
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargar()
  }, [])

  const abrirCrear = () => {
    setForm({ nombre: '', descripcion: '' })
    setModal('crear')
  }

  const abrirEditar = (curso) => {
    setForm({ nombre: curso.nombre, descripcion: curso.descripcion || '' })
    setModal(curso)
  }

  const guardar = async () => {
    if (!form.nombre.trim()) return
    setSaving(true)
    setError(null)
    try {
      if (modal === 'crear') {
        const nuevo = await createCurso(form)
        setCursos((prev) => [nuevo, ...prev])
      } else {
        const actualizado = await updateCurso(modal.id, form)
        setCursos((prev) => prev.map((c) => (c.id === actualizado.id ? actualizado : c)))
      }
      setModal(null)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setSaving(false)
    }
  }

  const eliminar = async (curso) => {
    if (!confirm(`¿Eliminar "${curso.nombre}"?`)) return
    try {
      await deleteCurso(curso.id)
      setCursos((prev) => prev.filter((c) => c.id !== curso.id))
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    }
  }

  const inscribir = async () => {
    const limpio = codigo.trim().toUpperCase()
    if (!limpio || saving) return
    setSaving(true)
    setError(null)
    try {
      const curso = await inscribirCurso(limpio)
      setCursos((prev) => (prev.some((c) => c.id === curso.id) ? prev : [curso, ...prev]))
      setCodigo('')
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <Navbar breadcrumb="Cursos" />
      <main style={s.main}>
        <SectionHead
          eyebrow={isDocente ? 'Tus cursos' : 'Cursos inscritos'}
          title={isDocente ? 'Mis cursos' : 'Mis cursos'}
          action={
            isDocente && (
              <button type="button" className="btn btn-primary" onClick={abrirCrear}>
                <Icon name="plus" size={14} />
                Nuevo curso
              </button>
            )
          }
        />

        {!isDocente && (
          <section className="card" style={s.joinCard}>
            <div style={{ flex: 1, minWidth: 240 }}>
              <div className="t-eyebrow" style={{ marginBottom: 6 }}>Unirme a un curso</div>
              <p className="t-muted" style={{ fontSize: 13 }}>
                Pídele a tu docente el código del curso (suele ser algo como{' '}
                <span className="t-mono">TIA-302</span>).
              </p>
            </div>
            <div style={s.joinRow}>
              <input
                className="field-input"
                style={{ minWidth: 200, flex: 1 }}
                value={codigo}
                onChange={(e) => setCodigo(e.target.value.toUpperCase())}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') inscribir()
                }}
                placeholder="CÓDIGO DEL CURSO"
                maxLength={16}
                aria-label="Código del curso"
              />
              <button
                type="button"
                className="btn btn-primary"
                onClick={inscribir}
                disabled={!codigo.trim() || saving}
              >
                {saving ? 'Uniendo…' : 'Unirme'}
              </button>
            </div>
          </section>
        )}

        {error && <p style={s.error}>{error}</p>}

        {loading ? (
          <p className="t-muted">Cargando cursos…</p>
        ) : cursos.length === 0 ? (
          <div className="card" style={s.emptyCard}>
            <p style={{ marginBottom: 14 }}>
              {isDocente
                ? 'Aún no tienes cursos. Crea uno para empezar a subir material.'
                : 'Aún no estás inscrito en ningún curso.'}
            </p>
            {isDocente && (
              <button type="button" className="btn btn-primary" onClick={abrirCrear}>
                Crear primer curso
              </button>
            )}
          </div>
        ) : (
          <div style={s.grid}>
            {cursos.map((c, i) => (
              <article key={c.id} className="card" style={s.card}>
                <CourseCover variant={colorForIndex(i)} size="short" />
                <div style={{ padding: 18, display: 'flex', flexDirection: 'column', flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <span className="t-mono t-tiny" style={{ color: 'var(--ink-500)' }}>
                      {c.codigo}
                    </span>
                  </div>
                  <h3 style={{ marginBottom: 6, lineHeight: 1.2 }}>{c.nombre}</h3>
                  {c.descripcion && (
                    <p
                      className="t-tiny t-muted"
                      style={{
                        marginBottom: 14,
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                      }}
                    >
                      {c.descripcion}
                    </p>
                  )}

                  <div style={{ flex: 1 }} />

                  <div style={s.cardActions}>
                    <button
                      type="button"
                      className="btn btn-primary"
                      style={{ padding: '9px 16px', fontSize: 13 }}
                      onClick={() =>
                        isDocente
                          ? navigate(`/cursos/${c.id}`)
                          : navigate(`/chat/${c.id}`)
                      }
                    >
                      {isDocente ? (
                        <>
                          <Icon name="file" size={14} />
                          Ver material
                        </>
                      ) : (
                        <>
                          <Icon name="chat" size={14} />
                          Chatear
                        </>
                      )}
                    </button>
                    {isDocente && (
                      <>
                        <button
                          type="button"
                          className="btn btn-ghost"
                          style={{ padding: '8px 12px', fontSize: 13 }}
                          onClick={() => abrirEditar(c)}
                          title="Editar"
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger"
                          style={{ padding: '8px 12px', fontSize: 13 }}
                          onClick={() => eliminar(c)}
                          title="Eliminar"
                        >
                          <Icon name="trash" size={14} />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}

        {modal && (
          <div style={s.overlay} onClick={() => !saving && setModal(null)}>
            <div
              className="card card-elev"
              style={s.modalCard}
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
            >
              <h2 style={{ marginBottom: 18 }}>
                {modal === 'crear' ? 'Nuevo curso' : 'Editar curso'}
              </h2>

              <label className="field-label" htmlFor="curso-nombre">
                Nombre *
              </label>
              <input
                id="curso-nombre"
                className="field-input"
                value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                placeholder="Ej: Algoritmos y Estructuras de Datos"
                autoFocus
                style={{ marginBottom: 14 }}
              />

              <label className="field-label" htmlFor="curso-desc">
                Descripción
              </label>
              <textarea
                id="curso-desc"
                className="field-input"
                value={form.descripcion}
                onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
                placeholder="Descripción breve del curso…"
                rows={3}
                style={{ resize: 'vertical', minHeight: 90, marginBottom: 12 }}
              />

              {error && <p style={s.error}>{error}</p>}

              <div style={s.modalActions}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setModal(null)}
                  disabled={saving}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={guardar}
                  disabled={!form.nombre.trim() || saving}
                >
                  {saving ? 'Guardando…' : 'Guardar'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  )
}

const s = {
  main: { maxWidth: 'var(--maxw)', margin: '0 auto', padding: '32px 24px 80px' },
  joinCard: {
    padding: 18,
    display: 'flex',
    alignItems: 'center',
    gap: 18,
    flexWrap: 'wrap',
    marginBottom: 28,
    background: 'linear-gradient(135deg, var(--mint-100), var(--surface) 80%)',
  },
  joinRow: { display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' },
  error: {
    color: 'var(--danger)',
    fontSize: 13,
    marginBottom: 14,
    background: 'rgba(214,90,71,.07)',
    border: '1px solid rgba(214,90,71,.25)',
    borderRadius: 'var(--r-sm)',
    padding: '8px 12px',
  },
  emptyCard: { padding: 28, textAlign: 'center', color: 'var(--ink-700)' },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: 18,
  },
  card: {
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  cardActions: { display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' },
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(26, 22, 20, .45)',
    backdropFilter: 'blur(4px)',
    WebkitBackdropFilter: 'blur(4px)',
    display: 'grid',
    placeItems: 'center',
    padding: 16,
    zIndex: 100,
  },
  modalCard: { width: '100%', maxWidth: 480, padding: 28 },
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 10,
    marginTop: 14,
  },
}
