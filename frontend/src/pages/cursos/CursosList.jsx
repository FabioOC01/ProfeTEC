import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCursos, createCurso, updateCurso, deleteCurso } from '../../api/cursos.js'

export default function CursosList() {
  const navigate = useNavigate()
  const [cursos, setCursos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modal, setModal] = useState(null) // null | 'crear' | curso (editar)
  const [form, setForm] = useState({ nombre: '', descripcion: '' })
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

  useEffect(() => { cargar() }, [])

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

  return (
    <main style={s.main}>
      <header style={s.header}>
        <div>
          <button onClick={() => navigate('/dashboard')} style={s.btnBack}>← Dashboard</button>
          <h1 style={s.titulo}>Mis cursos</h1>
        </div>
        <button onClick={abrirCrear} style={s.btnPrimario}>+ Nuevo curso</button>
      </header>

      {error && <p style={s.error}>{error}</p>}

      {loading ? (
        <p style={s.dim}>Cargando cursos…</p>
      ) : cursos.length === 0 ? (
        <div style={s.vacio}>
          <p>Aún no tienes cursos.</p>
          <button onClick={abrirCrear} style={s.btnPrimario}>Crear primer curso</button>
        </div>
      ) : (
        <div style={s.grid}>
          {cursos.map((c) => (
            <div key={c.id} style={s.card}>
              <div style={s.cardTop}>
                <strong style={s.cardNombre}>{c.nombre}</strong>
                <span style={s.codigo}>{c.codigo}</span>
              </div>
              {c.descripcion && <p style={s.cardDesc}>{c.descripcion}</p>}
              <div style={s.cardActions}>
                <button onClick={() => navigate(`/cursos/${c.id}`)} style={{ ...s.btnSmall, background: '#2f81f7', color: '#fff', border: 'none' }}>Ver material</button>
                <button onClick={() => abrirEditar(c)} style={s.btnSmall}>Editar</button>
                <button onClick={() => eliminar(c)} style={{ ...s.btnSmall, color: 'var(--error)' }}>
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {modal && (
        <div style={s.overlay}>
          <div style={s.modalCard}>
            <h2 style={s.modalTitulo}>
              {modal === 'crear' ? 'Nuevo curso' : 'Editar curso'}
            </h2>

            <label style={s.label}>Nombre *</label>
            <input
              style={s.input}
              value={form.nombre}
              onChange={(e) => setForm({ ...form, nombre: e.target.value })}
              placeholder="Ej: Algoritmos y Estructuras de Datos"
              autoFocus
            />

            <label style={s.label}>Descripción</label>
            <textarea
              style={{ ...s.input, minHeight: 80, resize: 'vertical' }}
              value={form.descripcion}
              onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
              placeholder="Descripción breve del curso…"
            />

            {error && <p style={s.error}>{error}</p>}

            <div style={s.modalActions}>
              <button onClick={() => setModal(null)} style={s.btnSmall}>Cancelar</button>
              <button
                onClick={guardar}
                disabled={!form.nombre.trim() || saving}
                style={{ ...s.btnPrimario, opacity: !form.nombre.trim() || saving ? 0.5 : 1 }}
              >
                {saving ? 'Guardando…' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}

const s = {
  main: { minHeight: '100vh', padding: '1.5rem', maxWidth: 900, margin: '0 auto' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '1.5rem' },
  btnBack: { fontSize: '0.8rem', marginBottom: '0.5rem', background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: 0 },
  titulo: { margin: 0, fontSize: '1.5rem' },
  btnPrimario: { background: '#2f81f7', color: '#fff', border: 'none', borderRadius: 8, padding: '0.5rem 1.25rem', cursor: 'pointer', fontWeight: 600 },
  error: { color: 'var(--error)', marginBottom: '1rem', fontSize: '0.875rem' },
  dim: { color: 'var(--text-dim)' },
  vacio: { textAlign: 'center', paddingTop: '4rem', color: 'var(--text-dim)' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '1rem' },
  card: { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1.25rem' },
  cardTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' },
  cardNombre: { fontSize: '1rem' },
  codigo: { fontSize: '0.7rem', background: 'var(--border)', padding: '0.2rem 0.5rem', borderRadius: 4, color: 'var(--text-dim)' },
  cardDesc: { fontSize: '0.825rem', color: 'var(--text-dim)', margin: '0 0 1rem' },
  cardActions: { display: 'flex', gap: '0.5rem' },
  btnSmall: { fontSize: '0.8rem', padding: '0.3rem 0.75rem', borderRadius: 6 },
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'grid', placeItems: 'center', zIndex: 100 },
  modalCard: { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '2rem', width: '100%', maxWidth: 460 },
  modalTitulo: { margin: '0 0 1.5rem', fontSize: '1.25rem' },
  label: { display: 'block', fontSize: '0.875rem', color: 'var(--text-dim)', marginBottom: '0.35rem' },
  input: { width: '100%', background: '#0a0d12', border: '1px solid var(--border)', borderRadius: 6, padding: '0.6rem 0.75rem', color: 'var(--text)', fontSize: '0.95rem', marginBottom: '1rem', boxSizing: 'border-box' },
  modalActions: { display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' },
}
