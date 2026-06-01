import { useEffect, useRef, useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { getCurso } from '../../api/cursos.js'
import {
  deleteDocumento,
  getCoberturaDocumentos,
  getDocumentos,
  uploadDocumento,
} from '../../api/documentos.js'
import { diagnosticarRag, getAnalytics } from '../../api/chat.js'
import { useAuth } from '../../context/AuthContext.jsx'
import Navbar from '../../components/Navbar.jsx'
import Icon from '../../components/ui/Icon.jsx'
import SectionHead from '../../components/ui/SectionHead.jsx'

const TIPOS_ACEPTADOS = '.pdf,.pptx,.txt'
const UPLOAD_INICIAL = { file: null, titulo: '', semana: '', referencia: '' }
const ICONOS = { pdf: '📄', pptx: '📊', txt: '📝' }

function tituloDesdeArchivo(file) {
  return (file?.name || '').replace(/\.[^/.]+$/, '')
}

export default function CursoDetalle() {
  const { cursoId } = useParams()
  const navigate = useNavigate()
  const { profile, viewMode } = useAuth()
  const isDocenteView = viewMode === 'docente'

  // En vista estudiante, el detalle del curso se reemplaza por el tutor.
  if (profile && !isDocenteView) {
    return <Navigate to={`/chat/${cursoId}`} replace />
  }

  return <CursoDetalleDocente cursoId={cursoId} navigate={navigate} />
}

function CursoDetalleDocente({ cursoId, navigate }) {
  const inputRef = useRef(null)
  const { profile } = useAuth()
  const canManage = profile?.rol === 'docente'
  const [curso, setCurso] = useState(null)
  const [documentos, setDocumentos] = useState([])
  const [cobertura, setCobertura] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadingAnalytics, setLoadingAnalytics] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progreso, setProgreso] = useState(0)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadDraft, setUploadDraft] = useState(UPLOAD_INICIAL)
  const [dragActive, setDragActive] = useState(false)
  const [ragPregunta, setRagPregunta] = useState('')
  const [ragDiagnostico, setRagDiagnostico] = useState(null)
  const [diagnosticando, setDiagnosticando] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelado = false

    const cargarPrincipal = async () => {
      setLoading(true)
      setError(null)
      setAnalytics(null)
      try {
        const [c, docs, cov] = await Promise.all([
          getCurso(cursoId),
          getDocumentos(cursoId),
          getCoberturaDocumentos(cursoId),
        ])
        if (cancelado) return
        setCurso(c)
        setDocumentos(docs)
        setCobertura(cov)
      } catch (e) {
        if (cancelado) return
        setError(e.response?.data?.detail || e.message)
      } finally {
        if (!cancelado) setLoading(false)
      }
    }

    const cargarAnalytics = async () => {
      if (!canManage) return
      setLoadingAnalytics(true)
      try {
        const metricas = await getAnalytics(cursoId)
        if (!cancelado) setAnalytics(metricas)
      } catch {
        if (!cancelado) setAnalytics(null)
      } finally {
        if (!cancelado) setLoadingAnalytics(false)
      }
    }

    cargarPrincipal()
    cargarAnalytics()

    return () => {
      cancelado = true
    }
  }, [cursoId, canManage])

  const refreshCobertura = () => {
    getCoberturaDocumentos(cursoId).then(setCobertura).catch(() => {})
  }

  const prepararArchivo = (file) => {
    if (!file || uploading) return
    if (!canManage) return
    setError(null)
    setUploadOpen(true)
    setUploadDraft((prev) => ({
      ...prev,
      file,
      titulo: prev.titulo || tituloDesdeArchivo(file),
    }))
  }

  const handleFile = (e) => {
    const file = e.target.files?.[0]
    prepararArchivo(file)
    if (inputRef.current) inputRef.current.value = ''
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragActive(false)
    prepararArchivo(e.dataTransfer.files?.[0])
  }

  const cerrarUpload = () => {
    if (uploading) return
    setUploadOpen(false)
    setUploadDraft(UPLOAD_INICIAL)
    setDragActive(false)
  }

  const handleUploadSubmit = async (e) => {
    e.preventDefault()
    const file = uploadDraft.file
    const titulo = uploadDraft.titulo.trim()
    const semana = Number(uploadDraft.semana)
    const referencia = uploadDraft.referencia.trim()
    if (!file || !titulo || !semana) return
    if (!canManage) return
    setError(null)
    setUploading(true)
    setProgreso(0)
    try {
      const nuevo = await uploadDocumento(
        cursoId,
        file,
        { titulo, semana, referencia },
        setProgreso,
      )
      setDocumentos((prev) => [nuevo, ...prev])
      setAnalytics((prev) => (
        prev
          ? {
              ...prev,
              total_documentos: (prev.total_documentos ?? 0) + 1,
              total_chunks: (prev.total_chunks ?? 0) + (nuevo.chunks_count ?? 0),
            }
          : prev
      ))
      setUploadOpen(false)
      setUploadDraft(UPLOAD_INICIAL)
      setDragActive(false)
      refreshCobertura()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setUploading(false)
      setProgreso(0)
    }
  }

  const handleDelete = async (doc) => {
    if (!confirm(`¿Eliminar "${doc.nombre}" y todos sus chunks?`)) return
    if (!canManage) return
    const snapshot = documentos
    setError(null)
    setDocumentos((prev) => prev.filter((d) => d.id !== doc.id))
    setAnalytics((prev) => (
      prev
        ? {
            ...prev,
            total_documentos: Math.max(0, (prev.total_documentos ?? 0) - 1),
            total_chunks: Math.max(0, (prev.total_chunks ?? 0) - (doc.chunks_count ?? 0)),
          }
        : prev
    ))
    try {
      await deleteDocumento(cursoId, doc.id)
      refreshCobertura()
    } catch (err) {
      setDocumentos(snapshot)
      setAnalytics((prev) => (
        prev
          ? {
              ...prev,
              total_documentos: (prev.total_documentos ?? 0) + 1,
              total_chunks: (prev.total_chunks ?? 0) + (doc.chunks_count ?? 0),
            }
          : prev
      ))
      setError(err.response?.data?.detail || err.message)
    }
  }

  const handleDiagnostico = async (e) => {
    e.preventDefault()
    const pregunta = ragPregunta.trim()
    if (!pregunta || diagnosticando) return
    if (!canManage) return
    setDiagnosticando(true)
    setRagDiagnostico(null)
    setError(null)
    try {
      const data = await diagnosticarRag(cursoId, pregunta)
      setRagDiagnostico(data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setDiagnosticando(false)
    }
  }

  if (loading) {
    return (
      <>
        <Navbar breadcrumb="Cursos" />
        <main style={s.main}>
          <p className="t-muted">Cargando…</p>
        </main>
      </>
    )
  }

  const breadcrumb = curso?.nombre ? `Cursos › ${curso.nombre}` : 'Cursos'

  return (
    <>
      <Navbar breadcrumb={breadcrumb} />
      <main style={s.main}>
        {/* Header */}
        <header style={s.header}>
          <div style={{ minWidth: 0 }}>
            <button
              type="button"
              onClick={() => navigate('/cursos')}
              style={s.backLink}
            >
              <Icon name="chevron" size={12} style={{ transform: 'rotate(180deg)' }} /> Cursos
            </button>
            <h1 style={{ marginTop: 6 }}>{curso?.nombre}</h1>
            <div className="t-muted" style={{ marginTop: 6, fontSize: 14 }}>
              <code>{curso?.codigo}</code>
              {curso?.descripcion && <> · {curso.descripcion}</>}
            </div>
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
              type="button"
              className="btn btn-ghost"
              onClick={() => navigate(`/cursos/${cursoId}/quizzes`)}
            >
              <Icon name="sparkle" size={15} /> Quizzes
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setUploadOpen(true)}
              disabled={uploading || !canManage}
              title={canManage ? 'Subir documento' : 'Solo disponible para docentes reales'}
            >
              <Icon name="upload" size={15} />
              {uploading ? `Procesando ${progreso}%` : 'Subir documento'}
            </button>
          </div>
        </header>

        {uploading && (
          <div style={s.progressBar}>
            <div style={{ ...s.progressFill, width: `${progreso}%` }} />
          </div>
        )}

        {error && <p style={s.error}>{error}</p>}

        {!canManage && (
          <p style={s.notice}>
            Estás viendo la interfaz de docente en modo previsualización. Puedes revisar el
            material y la cobertura, pero subir, eliminar o diagnosticar RAG requiere rol docente.
          </p>
        )}

        {uploadOpen && canManage && (
          <div style={s.overlay} onClick={cerrarUpload}>
            <form
              className="card card-elev"
              style={s.uploadModal}
              onClick={(e) => e.stopPropagation()}
              onSubmit={handleUploadSubmit}
            >
              <div style={s.modalHeader}>
                <div>
                  <div className="t-eyebrow">Nuevo material</div>
                  <h2 style={{ marginTop: 4 }}>Preparar documento</h2>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={cerrarUpload}
                  disabled={uploading}
                  style={{ padding: '8px 10px' }}
                >
                  <Icon name="x" size={15} />
                </button>
              </div>

              <div
                style={{
                  ...s.dropzone,
                  borderColor: dragActive ? 'var(--ink-900)' : 'var(--ink-100)',
                  background: dragActive ? 'var(--paper-2)' : 'var(--surface)',
                }}
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragActive(true)
                }}
                onDragLeave={() => setDragActive(false)}
                onDrop={handleDrop}
              >
                <Icon name="upload" size={20} />
                <strong>
                  {uploadDraft.file ? uploadDraft.file.name : 'Arrastra un archivo o haz clic'}
                </strong>
                <span className="t-tiny t-muted">PDF, PPTX o TXT · max. 20 MB</span>
              </div>

              <label className="field-label" htmlFor="doc-titulo">
                Titulo *
              </label>
              <input
                id="doc-titulo"
                className="field-input"
                value={uploadDraft.titulo}
                onChange={(e) => setUploadDraft({ ...uploadDraft, titulo: e.target.value })}
                placeholder="Ej. Semana 1 - Perfil del egresado"
                maxLength={160}
                disabled={uploading}
                style={{ marginBottom: 12 }}
                required
              />

              <label className="field-label" htmlFor="doc-semana">
                Semana *
              </label>
              <input
                id="doc-semana"
                className="field-input"
                type="number"
                min={1}
                max={30}
                value={uploadDraft.semana}
                onChange={(e) => setUploadDraft({ ...uploadDraft, semana: e.target.value })}
                placeholder="Ej. 1"
                disabled={uploading}
                style={{ marginBottom: 12 }}
                required
              />

              <label className="field-label" htmlFor="doc-referencia">
                Referencia
              </label>
              <textarea
                id="doc-referencia"
                className="field-input"
                value={uploadDraft.referencia}
                onChange={(e) => setUploadDraft({ ...uploadDraft, referencia: e.target.value })}
                placeholder="Ej. Clase teorica, lectura base, laboratorio, enlace o nota interna"
                maxLength={300}
                rows={3}
                disabled={uploading}
                style={{ resize: 'vertical', minHeight: 84, marginBottom: 12 }}
              />

              {uploading && (
                <div style={s.progressBar}>
                  <div style={{ ...s.progressFill, width: `${progreso}%` }} />
                </div>
              )}

              <div style={s.modalActions}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={cerrarUpload}
                  disabled={uploading}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={
                    uploading ||
                    !uploadDraft.file ||
                    !uploadDraft.titulo.trim() ||
                    !uploadDraft.semana
                  }
                >
                  {uploading ? `Procesando ${progreso}%` : 'Subir e indexar'}
                </button>
              </div>
            </form>
          </div>
        )}

        {analytics && (
          <section style={s.metrics}>
            <Metric value={analytics.total_mensajes} label="mensajes" />
            <Metric value={analytics.total_conversaciones} label="conversaciones" />
            <Metric value={analytics.estudiantes_matriculados} label="estudiantes" />
            <Metric value={analytics.total_documentos} label="documentos" />
            <Metric
              value={analytics.feedback_positivo}
              label="útiles"
              color="var(--mint-700)"
            />
            <Metric
              value={analytics.feedback_negativo}
              label="a mejorar"
              color="var(--danger)"
            />
          </section>
        )}
        {!analytics && loadingAnalytics && (
          <p className="t-muted" style={{ marginBottom: 24, fontSize: 13 }}>
            Actualizando metricas del curso...
          </p>
        )}

        {cobertura && (
          <section style={s.ragGrid}>
            <div className="card" style={s.ragPanel}>
              <SectionHead
                eyebrow="Cobertura RAG"
                title="Semanas con material indexado"
              />
              {cobertura.semanas.length === 0 ? (
                <p className="t-muted" style={{ fontSize: 13 }}>
                  Todavía no hay semanas indexadas.
                </p>
              ) : (
                <div style={s.weekChips}>
                  {cobertura.semanas.map((semana) => {
                    const ok = semana.chunks > 0
                    return (
                      <span
                        key={semana.semana}
                        style={{
                          ...s.weekChip,
                          borderColor: ok ? 'var(--mint-500)' : 'var(--danger)',
                          background: ok ? 'var(--mint-100)' : 'rgba(214,90,71,.07)',
                          color: ok ? 'var(--mint-700)' : 'var(--danger)',
                        }}
                        title={semana.nombres.join(', ')}
                      >
                        S{semana.semana} · {semana.chunks} chunks
                      </span>
                    )
                  })}
                </div>
              )}
              <p className="t-tiny t-muted" style={{ marginTop: 12 }}>
                {cobertura.total_chunks} chunks en {cobertura.total_documentos} documentos.
                {cobertura.semanas_sin_chunks.length > 0 && (
                  <> Revisar semanas sin chunks: {cobertura.semanas_sin_chunks.join(', ')}.</>
                )}
              </p>
            </div>

            <div className="card" style={s.ragPanel}>
              <SectionHead
                eyebrow="Diagnóstico"
                title="Probar recuperación"
              />
              <form onSubmit={handleDiagnostico} style={s.diagnosticForm}>
                <input
                  className="field-input"
                  value={ragPregunta}
                  onChange={(e) => setRagPregunta(e.target.value)}
                  placeholder="Ej. Resume los puntos clave de la semana 11"
                  disabled={diagnosticando || !canManage}
                />
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={diagnosticando || !ragPregunta.trim() || !canManage}
                  title={canManage ? 'Probar recuperación' : 'Solo disponible para docentes reales'}
                >
                  <Icon name="search" size={14} />
                  {diagnosticando ? 'Probando...' : 'Probar'}
                </button>
              </form>

              {ragDiagnostico && (
                <div style={s.diagnosticResult}>
                  <div className="t-tiny t-muted">
                    Semana detectada: {ragDiagnostico.semana_detectada ?? 'ninguna'} ·{' '}
                    {ragDiagnostico.total_chunks} chunks ·{' '}
                    {ragDiagnostico.contexto_debil ? 'contexto débil' : 'contexto sólido'}
                  </div>
                  {ragDiagnostico.chunks.length === 0 ? (
                    <p style={{ marginTop: 8, fontSize: 13 }}>
                      No se recuperó material para esta consulta.
                    </p>
                  ) : (
                    <div style={s.diagnosticChunks}>
                      {ragDiagnostico.chunks.slice(0, 4).map((chunk, i) => (
                        <div key={`${chunk.documento_id}-${chunk.pagina}-${i}`} style={s.diagnosticChunk}>
                          <strong>{chunk.nombre_doc}</strong>
                          <span className="t-tiny t-muted">
                            pág. {chunk.pagina} · score {chunk.score.toFixed(2)}
                            {chunk.semana ? ` · semana ${chunk.semana}` : ''}
                            {chunk.metadata_match ? ' · metadata' : ''}
                          </span>
                          <p>{chunk.fragmento}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        )}

        <SectionHead
          eyebrow="Indexado y disponible para el tutor"
          title={`Material del curso (${documentos.length})`}
        />

        {documentos.length === 0 ? (
          <div className="card" style={s.emptyCard}>
            <p style={{ marginBottom: 8 }}>No hay documentos aún.</p>
            <p className="t-muted" style={{ marginBottom: 16 }}>
              Sube un PDF, PPTX o TXT para que el tutor pueda responder con citas.
            </p>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setUploadOpen(true)}
            >
              Subir primer documento
            </button>
          </div>
        ) : (
          <div style={s.docsGrid}>
            {documentos.map((doc) => (
              <article key={doc.id} className="card" style={s.docCard}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                  <span style={s.docIcon}>{ICONOS[doc.tipo] || '📎'}</span>
                  <div style={{ minWidth: 0 }}>
                    <strong
                      style={{
                        display: 'block',
                        fontSize: 14,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {doc.nombre}
                    </strong>
                    <span className="t-tiny t-muted">
                      {doc.semana && <>Semana {doc.semana} · </>}
                      <span className="t-mono">{doc.tipo.toUpperCase()}</span> · {doc.paginas} pág. ·{' '}
                      {doc.chunks_count} chunks
                    </span>
                    {doc.referencia && (
                      <span
                        className="t-tiny t-muted"
                        style={{
                          display: 'block',
                          marginTop: 2,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {doc.referencia}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => handleDelete(doc)}
                  disabled={!canManage}
                  title={canManage ? 'Eliminar' : 'Solo disponible para docentes reales'}
                  style={{ padding: '6px 10px', fontSize: 12 }}
                >
                  <Icon name="trash" size={13} /> Eliminar
                </button>
              </article>
            ))}
          </div>
        )}
      </main>
    </>
  )
}

function Metric({ value, label, color = 'var(--ink-900)' }) {
  return (
    <div className="card" style={s.metric}>
      <strong
        style={{
          fontFamily: 'var(--font-display)',
          fontSize: 24,
          color,
          lineHeight: 1,
        }}
      >
        {value ?? 0}
      </strong>
      <span className="t-tiny t-muted" style={{ marginTop: 4 }}>{label}</span>
    </div>
  )
}

const s = {
  main: { maxWidth: 'var(--maxw)', margin: '0 auto', padding: '32px 24px 80px' },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    gap: 16,
    marginBottom: 24,
    flexWrap: 'wrap',
  },
  backLink: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    background: 'transparent',
    border: 'none',
    color: 'var(--ink-500)',
    fontSize: 13,
    cursor: 'pointer',
    padding: 0,
  },
  actions: {
    display: 'flex',
    gap: 10,
    flexShrink: 0,
    alignItems: 'flex-end',
    flexWrap: 'wrap',
  },
  weekField: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    minWidth: 92,
  },
  weekInput: {
    height: 38,
    width: 92,
    padding: '8px 10px',
  },
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
  uploadModal: {
    width: '100%',
    maxWidth: 560,
    padding: 24,
  },
  modalHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
    marginBottom: 16,
  },
  dropzone: {
    minHeight: 130,
    border: '1px dashed var(--ink-100)',
    borderRadius: 'var(--r-md)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    padding: 18,
    marginBottom: 16,
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'background .15s ease, border-color .15s ease',
  },
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 10,
    marginTop: 12,
    flexWrap: 'wrap',
  },
  progressBar: {
    height: 4,
    background: 'var(--ink-100)',
    borderRadius: 2,
    marginBottom: 16,
    overflow: 'hidden',
  },
  progressFill: { height: '100%', background: 'var(--amber-500)', transition: 'width .3s ease' },
  error: {
    color: 'var(--danger)',
    fontSize: 13,
    marginBottom: 14,
    background: 'rgba(214,90,71,.07)',
    border: '1px solid rgba(214,90,71,.25)',
    borderRadius: 'var(--r-sm)',
    padding: '8px 12px',
  },
  notice: {
    color: 'var(--amber-700)',
    fontSize: 13,
    marginBottom: 14,
    background: 'var(--amber-100)',
    border: '1px solid var(--amber-200)',
    borderRadius: 'var(--r-sm)',
    padding: '8px 12px',
  },
  metrics: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: 12,
    marginBottom: 32,
  },
  metric: {
    padding: '16px 18px',
    display: 'flex',
    flexDirection: 'column',
  },
  ragGrid: {
    display: 'grid',
    gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.15fr)',
    gap: 12,
    marginBottom: 32,
  },
  ragPanel: {
    padding: 18,
    minWidth: 0,
  },
  weekChips: {
    display: 'flex',
    gap: 8,
    flexWrap: 'wrap',
  },
  weekChip: {
    display: 'inline-flex',
    alignItems: 'center',
    minHeight: 28,
    padding: '5px 9px',
    border: '1px solid var(--ink-100)',
    borderRadius: 'var(--r-pill)',
    fontSize: 12,
    fontWeight: 600,
  },
  diagnosticForm: {
    display: 'grid',
    gridTemplateColumns: 'minmax(0, 1fr) auto',
    gap: 8,
    alignItems: 'center',
  },
  diagnosticResult: {
    marginTop: 12,
    borderTop: '1px solid var(--ink-100)',
    paddingTop: 12,
  },
  diagnosticChunks: {
    display: 'grid',
    gap: 8,
    marginTop: 10,
  },
  diagnosticChunk: {
    padding: 10,
    border: '1px solid var(--ink-100)',
    borderRadius: 'var(--r-sm)',
    background: 'var(--paper-2)',
    fontSize: 12.5,
    lineHeight: 1.45,
  },
  emptyCard: { padding: 28, textAlign: 'center' },
  docsGrid: {
    display: 'grid',
    gap: 10,
  },
  docCard: {
    padding: '14px 18px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 14,
  },
  docIcon: { fontSize: 22, flexShrink: 0 },
}
