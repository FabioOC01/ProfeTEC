import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getCurso } from '../../api/cursos.js'
import { deleteDocumento, getDocumentos, uploadDocumento } from '../../api/documentos.js'
import { enviarPregunta, getHistorial } from '../../api/chat.js'
import { useAuth } from '../../context/AuthContext.jsx'
import Navbar from '../../components/Navbar.jsx'

const TIPOS_ACEPTADOS = '.pdf,.pptx,.txt'
const ICONOS = { pdf: '📄', pptx: '📊', txt: '📝' }

export default function CursoDetalle() {
  const { cursoId } = useParams()
  const { profile } = useAuth()
  const isDocente = profile?.rol === 'docente'

  // ── Refs ──────────────────────────────────────────────────────────────────
  const inputRef = useRef(null)
  const chatEndRef = useRef(null)
  const preguntaRef = useRef(null)

  // ── Estado del curso ──────────────────────────────────────────────────────
  const [curso, setCurso] = useState(null)
  const [documentos, setDocumentos] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [progreso, setProgreso] = useState(0)
  const [error, setError] = useState(null)

  // ── Estado del chat ───────────────────────────────────────────────────────
  const [mensajes, setMensajes] = useState([])          // {id, pregunta, respuesta, chunks_usados}
  const [conversacionId, setConversacionId] = useState(null)
  const [pregunta, setPregunta] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [chatError, setChatError] = useState(null)
  const [citasAbiertas, setCitasAbiertas] = useState({}) // msgId → bool

  // ── Carga inicial ─────────────────────────────────────────────────────────
  useEffect(() => {
    const cargar = async () => {
      try {
        const [c, historial] = await Promise.all([
          getCurso(cursoId),
          getHistorial(cursoId),
        ])
        setCurso(c)
        setMensajes(historial)
        if (historial.length > 0) {
          // Intentar recuperar conversacion_id del primer mensaje (no disponible en historial)
          // Se asignará cuando el usuario envíe el primer mensaje nuevo
        }

        // Solo docentes ven la lista de documentos
        if (isDocente) {
          const docs = await getDocumentos(cursoId)
          setDocumentos(docs)
        }
      } catch (e) {
        setError(e.response?.data?.detail || e.message)
      } finally {
        setLoading(false)
      }
    }
    cargar()
  }, [cursoId, isDocente])

  // Scroll al final del chat cuando llegan nuevos mensajes
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes, enviando])

  // ── Handlers de documentos ────────────────────────────────────────────────
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

  // ── Handler de chat ───────────────────────────────────────────────────────
  const enviar = async () => {
    const texto = pregunta.trim()
    if (!texto || enviando) return

    setChatError(null)
    setEnviando(true)
    setPregunta('')

    // Agregar mensaje optimista (sin respuesta aún)
    const tempId = `temp-${Date.now()}`
    setMensajes((prev) => [...prev, { id: tempId, pregunta: texto, respuesta: null, chunks_usados: [] }])

    try {
      const data = await enviarPregunta(cursoId, texto, conversacionId)
      setConversacionId(data.conversacion_id)
      // Reemplazar mensaje temporal con el real
      setMensajes((prev) =>
        prev.map((m) =>
          m.id === tempId
            ? {
                id: data.mensaje_id,
                pregunta: texto,
                respuesta: data.respuesta,
                chunks_usados: data.chunks_usados,
                creado_en: data.creado_en,
              }
            : m
        )
      )
    } catch (err) {
      setChatError(err.response?.data?.detail || err.message)
      // Quitar mensaje temporal en caso de error
      setMensajes((prev) => prev.filter((m) => m.id !== tempId))
    } finally {
      setEnviando(false)
      preguntaRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      enviar()
    }
  }

  const toggleCitas = (msgId) =>
    setCitasAbiertas((prev) => ({ ...prev, [msgId]: !prev[msgId] }))

  // ── Render ─────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <>
        <Navbar breadcrumb="Cursos" />
        <main style={s.main}><p style={s.dim}>Cargando…</p></main>
      </>
    )
  }

  const breadcrumb = curso?.nombre ? `Cursos › ${curso.nombre}` : 'Cursos'

  return (
    <>
      <Navbar breadcrumb={breadcrumb} />
      <main style={s.main}>
        {/* ── Header ── */}
        <header style={s.header}>
          <div>
            <h1 style={s.titulo}>{curso?.nombre}</h1>
            <p style={s.sub}>
              Código: <code style={s.code}>{curso?.codigo}</code>
              {curso?.descripcion && ` · ${curso.descripcion}`}
            </p>
          </div>
          {isDocente && (
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
          )}
        </header>

      {uploading && (
        <div style={s.progressBar}>
          <div style={{ ...s.progressFill, width: `${progreso}%` }} />
        </div>
      )}

      {error && <p style={s.error}>{error}</p>}

      {/* ── Material del curso (solo docentes) ── */}
      {isDocente && (
        <section style={{ marginBottom: '2rem' }}>
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
                  <button onClick={() => handleDelete(doc)} style={s.btnDelete}>
                    Eliminar
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Chat con el tutor ── */}
      <section>
        <h2 style={s.h2}>
         Chat con ProfeTEC.IA
          {mensajes.length > 0 && (
            <span style={s.badge}>{mensajes.length} mensajes</span>
          )}
        </h2>

        <div style={s.chatBox}>
          {/* Mensajes vacíos */}
          {mensajes.length === 0 && !enviando && (
            <div style={s.chatVacio}>
              <p style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🤖</p>
              <p style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Hola, soy ProfeTEC.IA</p>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-dim)' }}>
                Hazme una pregunta sobre el material del curso y te responderé con citas del documento.
              </p>
            </div>
          )}

          {/* Lista de mensajes */}
          {mensajes.map((msg) => (
            <div key={msg.id} style={s.msgGroup}>
              {/* Pregunta del usuario */}
              <div style={s.msgUserRow}>
                <div style={s.msgUser}>{msg.pregunta}</div>
              </div>

              {/* Respuesta del tutor */}
              <div style={s.msgTutorRow}>
                <span style={s.avatarBot}>🤖</span>
                <div style={s.msgTutorWrap}>
                  {msg.respuesta === null ? (
                    <div style={s.msgTutor}>
                      <span style={s.typing}>●●●</span>
                    </div>
                  ) : (
                    <div style={s.msgTutor}>
                      <p style={{ margin: 0, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                        {msg.respuesta}
                      </p>
                      {/* Citas */}
                      {msg.chunks_usados?.length > 0 && (
                        <div style={{ marginTop: '0.75rem' }}>
                          <button
                            onClick={() => toggleCitas(msg.id)}
                            style={s.btnCitas}
                          >
                            {citasAbiertas[msg.id] ? '▲' : '▼'} {msg.chunks_usados.length} fuente{msg.chunks_usados.length > 1 ? 's' : ''}
                          </button>
                          {citasAbiertas[msg.id] && (
                            <div style={s.citasList}>
                              {msg.chunks_usados.map((c, i) => (
                                <div key={i} style={s.cita}>
                                  <span style={s.citaIcon}>📄</span>
                                  <div>
                                    <div style={s.citaNombre}>{c.nombre_doc} — pág. {c.pagina}</div>
                                    <div style={s.citaFragmento}>"{c.fragmento}…"</div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Indicador de error en chat */}
          {chatError && (
            <p style={{ ...s.error, textAlign: 'center', margin: '0.5rem 0' }}>
              ⚠️ {chatError}
            </p>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input de pregunta */}
        <div style={s.inputRow}>
          <textarea
            ref={preguntaRef}
            style={s.inputChat}
            value={pregunta}
            onChange={(e) => setPregunta(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe tu pregunta… (Enter para enviar, Shift+Enter para nueva línea)"
            disabled={enviando}
            rows={2}
          />
          <button
            onClick={enviar}
            disabled={!pregunta.trim() || enviando}
            style={{
              ...s.btnEnviar,
              opacity: !pregunta.trim() || enviando ? 0.5 : 1,
            }}
          >
            {enviando ? '…' : '➤'}
          </button>
        </div>
        <p style={s.chatHint}>
          Las respuestas se basan únicamente en el material subido al curso.
        </p>
      </section>
      </main>
    </>
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
  h2: { fontSize: '1rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' },
  badge: { fontSize: '0.7rem', background: 'var(--border)', padding: '0.2rem 0.5rem', borderRadius: 99, textTransform: 'none', letterSpacing: 0, color: 'var(--text-dim)' },
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
  // Chat
  chatBox: { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '1.25rem', minHeight: 300, maxHeight: 520, overflowY: 'auto', marginBottom: '0.75rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' },
  chatVacio: { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', color: 'var(--text-dim)', padding: '2rem' },
  msgGroup: { display: 'flex', flexDirection: 'column', gap: '0.5rem' },
  msgUserRow: { display: 'flex', justifyContent: 'flex-end' },
  msgUser: { background: '#2f81f7', color: '#fff', borderRadius: '12px 12px 4px 12px', padding: '0.6rem 1rem', maxWidth: '75%', fontSize: '0.9rem', lineHeight: 1.5 },
  msgTutorRow: { display: 'flex', alignItems: 'flex-start', gap: '0.5rem' },
  avatarBot: { fontSize: '1.2rem', flexShrink: 0, marginTop: '0.1rem' },
  msgTutorWrap: { maxWidth: '85%' },
  msgTutor: { background: 'var(--border)', borderRadius: '4px 12px 12px 12px', padding: '0.75rem 1rem', fontSize: '0.9rem', lineHeight: 1.6 },
  typing: { animation: 'pulse 1s infinite', fontSize: '1.2rem', letterSpacing: '0.2rem', color: 'var(--text-dim)' },
  btnCitas: { fontSize: '0.75rem', background: 'none', border: 'none', color: '#2f81f7', cursor: 'pointer', padding: '0.25rem 0', marginTop: '0.25rem' },
  citasList: { marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' },
  cita: { display: 'flex', gap: '0.5rem', background: 'rgba(47,129,247,0.08)', borderRadius: 6, padding: '0.4rem 0.6rem', border: '1px solid rgba(47,129,247,0.2)' },
  citaIcon: { flexShrink: 0 },
  citaNombre: { fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.1rem' },
  citaFragmento: { fontSize: '0.72rem', color: 'var(--text-dim)', fontStyle: 'italic' },
  inputRow: { display: 'flex', gap: '0.5rem', alignItems: 'flex-end' },
  inputChat: { flex: 1, background: '#0a0d12', border: '1px solid var(--border)', borderRadius: 8, padding: '0.65rem 0.875rem', color: 'var(--text)', fontSize: '0.9rem', resize: 'none', fontFamily: 'inherit', lineHeight: 1.5 },
  btnEnviar: { background: '#2f81f7', color: '#fff', border: 'none', borderRadius: 8, padding: '0 1.25rem', fontSize: '1.1rem', cursor: 'pointer', height: 56, flexShrink: 0 },
  chatHint: { fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.4rem', textAlign: 'center' },
}
