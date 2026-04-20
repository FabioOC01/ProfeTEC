import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getCurso } from '../../api/cursos.js'
import { deleteDocumento, getDocumentos, uploadDocumento } from '../../api/documentos.js'

const TIPOS_ACEPTADOS = '.pdf,.pptx,.txt'
const ICONOS = { pdf: '📄', pptx: '📊', txt: '📝' }

export default function CursoDetalle() {
  const { cursoId } = useParams()
  const navigate = useNavigate()
  const inputRef = useRef(null)

  const [curso, setCurso] = useState(null)
  const [documentos, setDocumentos] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [progreso, setProgreso] = useState(0)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([getCurso(cursoId), getDocumentos(cursoId)])
      .then(([c, docs]) => { setCurso(c); setDocumentos(docs) })
      .catch((e) => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [cursoId])

  const handleFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    setUploading(true)
    setProgreso(0)
    try {
      const nuevo = await uploadDocumento(cursoId, file, setProgreso)
      setDocumentos((prev) => [nuevo, ...prev])
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setUploading(false)
      setProgreso(0)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const handleDelete = async (doc) => {
    if (!confirm(`¿Eliminar "${doc.nombre}" y todos sus chunks?`)) return
    try {
      await deleteDocumento(cursoId, doc.id)
      setDocumentos((prev) => prev.filter((d) => d.id !== doc.id))
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  if (loading) return <p style={s.dim}>Cargando…</p>

  return (
    <main style={s.main}>
      <header style={s.header}>
        <div>
          <button onClick={() => navigate('/cursos')} style={s.btnBack}>← Mis cursos</button>
          <h1 style={s.titulo}>{curso?.nombre}</h1>
          <p style={s.sub}>
            Código: <code style={s.code}>{curso?.codigo}</code>
            {curso?.descripcion && ` · ${curso.descripcion}`}
          </p>
        </div>
        <div style={s.actions}>
          <input
            ref={inputRef}
            type="file"
            accept={TIPOS_ACEPTADOS}
            style={{ display: 'none' }}
            onChange={handleFile}
          />
          <button
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            style={{ ...s.btnPrimario, opacity: uploading ? 0.6 : 1 }}
          >
            {uploading ? `Procesando… ${progreso}%` : '+ Subir documento'}
          </button>
        </div>
      </header>

      {uploading && (
        <div style={s.progressBar}>
          <div style={{ ...s.progressFill, width: `${progreso}%` }} />
        </div>
      )}

      {error && <p style={s.error}>{error}</p>}

      <section>
        <h2 style={s.h2}>Material del curso ({documentos.length})</h2>

        {documentos.length === 0 ? (
          <div style={s.vacio}>
            <p>No hay documentos aún.</p>
            <p style={s.dim}>Sube un PDF, PPTx o TXT para que los estudiantes puedan consultarlo.</p>
            <button onClick={() => inputRef.current?.click()} style={s.btnPrimario}>
              Subir primer documento
            </button>
          </div>
        ) : (
          <div style={s.grid}>
            {documentos.map((doc) => (
              <div key={doc.id} style={s.card}>
                <div style={s.cardTop}>
                  <span style={s.icon}>{ICONOS[doc.tipo] || '📎'}</span>
                  <div style={s.cardInfo}>
                    <strong style={s.cardNombre}>{doc.nombre}</strong>
                    <span style={s.cardMeta}>
                      {doc.tipo.toUpperCase()} · {doc.paginas} pág. · {doc.chunks_count} chunks
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(doc)}
                  style={s.btnDelete}
                >
                  Eliminar
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section style={{ marginTop: '2rem' }}>
        <h2 style={s.h2}>Chat con el tutor</h2>
        <div style={s.chatPlaceholder}>
          💬 Disponible en Sprint 3 — RAG + Gemini
        </div>
      </section>
    </main>
  )
}

const s = {
  main: { minHeight: '100vh', padding: '1.5rem', maxWidth: 900, margin: '0 auto' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '1.5rem' },
  btnBack: { fontSize: '0.8rem', background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: 0, marginBottom: '0.5rem', display: 'block' },
  titulo: { margin: '0 0 0.25rem', fontSize: '1.5rem' },
  sub: { margin: 0, color: 'var(--text-dim)', fontSize: '0.875rem' },
  code: { background: 'var(--border)', padding: '0.1rem 0.4rem', borderRadius: 4, fontSize: '0.8rem' },
  actions: { flexShrink: 0 },
  btnPrimario: { background: '#2f81f7', color: '#fff', border: 'none', borderRadius: 8, padding: '0.5rem 1.25rem', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem' },
  progressBar: { height: 4, background: 'var(--border)', borderRadius: 2, marginBottom: '1rem', overflow: 'hidden' },
  progressFill: { height: '100%', background: '#2f81f7', transition: 'width 0.3s ease' },
  error: { color: 'var(--error)', fontSize: '0.875rem', marginBottom: '1rem' },
  h2: { fontSize: '1rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '1rem' },
  vacio: { textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-dim)' },
  dim: { color: 'var(--text-dim)' },
  grid: { display: 'grid', gap: '0.75rem' },
  card: { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1rem 1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  cardTop: { display: 'flex', alignItems: 'center', gap: '0.75rem' },
  icon: { fontSize: '1.5rem' },
  cardInfo: { display: 'flex', flexDirection: 'column', gap: '0.2rem' },
  cardNombre: { fontSize: '0.95rem' },
  cardMeta: { fontSize: '0.75rem', color: 'var(--text-dim)' },
  btnDelete: { fontSize: '0.8rem', padding: '0.3rem 0.75rem', borderRadius: 6, color: 'var(--error)', border: '1px solid var(--error)', background: 'transparent', cursor: 'pointer' },
  chatPlaceholder: { background: 'var(--card)', border: '1px dashed var(--border)', borderRadius: 10, padding: '2rem', textAlign: 'center', color: 'var(--text-dim)' },
}
