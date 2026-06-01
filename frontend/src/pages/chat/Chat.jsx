import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getCurso, getCursos } from '../../api/cursos.js'
import { getDocumentos } from '../../api/documentos.js'
import {
  enviarFeedback,
  enviarPregunta,
  enviarPreguntaStream,
  getConversaciones,
  getHistorial,
} from '../../api/chat.js'
import Navbar from '../../components/Navbar.jsx'
import TutorBlob from '../../components/ui/TutorBlob.jsx'
import Icon from '../../components/ui/Icon.jsx'
import CitationPopover from '../../components/ui/CitationPopover.jsx'
import { colorForIndex } from '../../components/ui/CourseCover.jsx'

const FALLBACK_SUGGESTIONS = [
  '¿Qué documentos hay disponibles en este curso?',
  'Ayúdame a repasar el material subido',
  'Hazme preguntas de repaso del curso',
]

const TYPE_CHARS_PER_TICK = 3
const TYPE_TICK_MS = 18

function limpiarTemaDocumento(doc) {
  const base = (doc?.referencia || doc?.nombre || 'el material').trim()
  return base
    .replace(/\.(pdf|pptx|txt)$/i, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function recortarTexto(texto, max = 58) {
  if (texto.length <= max) return texto
  return `${texto.slice(0, max - 1).trim()}…`
}

function sugerenciasDesdeDocumentos(documentos = []) {
  const docs = [...documentos]
    .filter((doc) => doc?.nombre && (doc.chunks_count ?? 0) > 0)
    .sort((a, b) => {
      const semanaA = a.semana ?? 999
      const semanaB = b.semana ?? 999
      if (semanaA !== semanaB) return semanaA - semanaB
      return String(a.nombre).localeCompare(String(b.nombre))
    })

  if (!docs.length) return FALLBACK_SUGGESTIONS

  const sugerencias = []
  const primero = docs[0]
  const temaPrimero = recortarTexto(limpiarTemaDocumento(primero), 48)
  sugerencias.push(
    primero.semana
      ? `Repasemos la semana ${primero.semana}: ${temaPrimero}`
      : `Explícame ${temaPrimero}`,
  )

  const segundo = docs[1] || docs[0]
  sugerencias.push(`Hazme preguntas sobre ${recortarTexto(limpiarTemaDocumento(segundo), 46)}`)

  const ultimo = docs[docs.length - 1]
  const temaUltimo = recortarTexto(limpiarTemaDocumento(ultimo), 48)
  sugerencias.push(
    ultimo.semana
      ? `Resume los puntos clave de la semana ${ultimo.semana}: ${temaUltimo}`
      : `Resume los puntos clave de ${temaUltimo}`,
  )

  return [...new Set(sugerencias)].slice(0, 3)
}

export default function Chat() {
  const { cursoId } = useParams()
  const navigate = useNavigate()

  const [cursos, setCursos] = useState([])
  const [curso, setCurso] = useState(null)
  const [documentos, setDocumentos] = useState([])
  const [mensajes, setMensajes] = useState([])
  const [conversaciones, setConversaciones] = useState([])
  const [conversacionId, setConversacionId] = useState(null)
  const [draft, setDraft] = useState('')
  const [modo, setModo] = useState(() => {
    const saved = sessionStorage.getItem('profetec-chat-mode')
    return saved === 'socratico' ? 'socratico' : 'directo'
  })
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)
  const [loadingHist, setLoadingHist] = useState(true)
  const [popover, setPopover] = useState(null) // { index, chunk, anchor }

  const scrollRef = useRef(null)
  const draftRef = useRef(null)
  const typingTimerRef = useRef(null)
  const typingQueueRef = useRef('')
  const pendingDoneRef = useRef(null)
  const suggestions = useMemo(() => sugerenciasDesdeDocumentos(documentos), [documentos])

  const stopTypingQueue = () => {
    if (typingTimerRef.current) clearTimeout(typingTimerRef.current)
    typingTimerRef.current = null
    typingQueueRef.current = ''
    pendingDoneRef.current = null
  }

  const finalizeStreamMessage = (tempId, text, data, sentMode) => {
    const eraNueva = !conversacionId
    setConversacionId(data.conversacion_id)
    if (eraNueva || !conversaciones.some((c) => c.id === data.conversacion_id)) {
      refreshConversaciones()
    }
    setMensajes((prev) =>
      prev.map((m) =>
        m.id === tempId
          ? {
              id: data.mensaje_id,
              pregunta: text,
              respuesta: data.respuesta,
              streaming: false,
              modo: data.modo || sentMode,
              chunks_usados: data.chunks_usados,
              creado_en: data.creado_en,
            }
          : m,
      ),
    )
    setEnviando(false)
    draftRef.current?.focus()
  }

  const pumpTypingQueue = (tempId, text, sentMode) => {
    if (typingTimerRef.current) return

    const tick = () => {
      const next = typingQueueRef.current.slice(0, TYPE_CHARS_PER_TICK)
      typingQueueRef.current = typingQueueRef.current.slice(TYPE_CHARS_PER_TICK)

      if (next) {
        setMensajes((prev) =>
          prev.map((m) =>
            m.id === tempId
              ? {
                  ...m,
                  respuesta: `${m.respuesta || ''}${next}`,
                  streamStage: 'generating',
                }
              : m,
          ),
        )
      }

      if (typingQueueRef.current) {
        typingTimerRef.current = setTimeout(tick, TYPE_TICK_MS)
        return
      }

      typingTimerRef.current = null
      if (pendingDoneRef.current) {
        const doneData = pendingDoneRef.current
        pendingDoneRef.current = null
        finalizeStreamMessage(tempId, text, doneData, sentMode)
      }
    }

    typingTimerRef.current = setTimeout(tick, TYPE_TICK_MS)
  }

  const enqueueText = (tempId, text, sentMode, delta) => {
    typingQueueRef.current += delta
    pumpTypingQueue(tempId, text, sentMode)
  }

  useEffect(() => {
    sessionStorage.setItem('profetec-chat-mode', modo)
  }, [modo])

  useEffect(() => stopTypingQueue, [])

  // Sidebar list of cursos
  useEffect(() => {
    getCursos().then(setCursos).catch(() => {})
  }, [])

  // Load curso + conversaciones (and the most recent thread) when cursoId changes
  useEffect(() => {
    let active = true
    stopTypingQueue()
    setLoadingHist(true)
    setMensajes([])
    setConversacionId(null)
    setConversaciones([])
    setDocumentos([])
    setPopover(null)
    Promise.all([getCurso(cursoId), getConversaciones(cursoId), getDocumentos(cursoId)])
      .then(async ([c, convs, docs]) => {
        if (!active) return
        setCurso(c)
        setConversaciones(convs)
        setDocumentos(docs)
        if (convs.length > 0) {
          const activa = convs[0] // backend las ordena de más reciente a más antigua
          setConversacionId(activa.id)
          const hist = await getHistorial(cursoId, activa.id)
          if (active) setMensajes(hist)
        }
      })
      .catch((e) => {
        if (active) setError(e.response?.data?.detail || e.message)
      })
      .finally(() => {
        if (active) setLoadingHist(false)
      })
    return () => {
      active = false
    }
  }, [cursoId])

  const refreshConversaciones = () => {
    getConversaciones(cursoId).then(setConversaciones).catch(() => {})
  }

  const selectConversacion = async (convId) => {
    if (convId === conversacionId || enviando) return
    stopTypingQueue()
    setPopover(null)
    setError(null)
    setConversacionId(convId)
    setMensajes([])
    setLoadingHist(true)
    try {
      const hist = await getHistorial(cursoId, convId)
      setMensajes(hist)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoadingHist(false)
    }
  }

  const nuevoChat = () => {
    if (enviando) return
    stopTypingQueue()
    setPopover(null)
    setError(null)
    setConversacionId(null)
    setMensajes([])
    draftRef.current?.focus()
  }

  // Autoscroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [mensajes, enviando])

  const send = async (textArg) => {
    const text = (textArg ?? draft).trim()
    if (!text || enviando) return
    setError(null)
    setDraft('')

    const tempId = `temp-${Date.now()}`
    setMensajes((prev) => [
      ...prev,
      {
        id: tempId,
        pregunta: text,
        respuesta: '',
        streaming: true,
        chunks_usados: [],
        modo,
      },
    ])
    setEnviando(true)

    try {
      let done = false

      await enviarPreguntaStream(cursoId, text, conversacionId, modo, {
        onStatus: ({ stage }) => {
          setMensajes((prev) =>
            prev.map((m) => (m.id === tempId ? { ...m, streamStage: stage } : m)),
          )
        },
        onMeta: (meta) => {
          setConversacionId(meta.conversacion_id)
          setMensajes((prev) =>
            prev.map((m) =>
              m.id === tempId
                ? {
                    ...m,
                    modo: meta.modo || modo,
                    chunks_usados: [],
                    pending_chunks_usados: meta.chunks_usados || [],
                  }
                : m,
            ),
          )
        },
        onDelta: (delta) => {
          enqueueText(tempId, text, modo, delta)
        },
        onDone: (data) => {
          done = true
          if (typingQueueRef.current || typingTimerRef.current) {
            pendingDoneRef.current = data
          } else {
            finalizeStreamMessage(tempId, text, data, modo)
          }
        },
      })

      if (!done) {
        throw new Error('La conexión de streaming terminó sin confirmar la respuesta.')
      }
    } catch (e) {
      stopTypingQueue()
      try {
        const data = await enviarPregunta(cursoId, text, conversacionId, modo)
        setConversacionId(data.conversacion_id)
        enqueueText(tempId, text, modo, data.respuesta || '')
        pendingDoneRef.current = data
      } catch (fallbackError) {
        setError(fallbackError.response?.data?.detail || fallbackError.message || e.message)
        setMensajes((prev) => prev.filter((m) => m.id !== tempId))
      }
      setEnviando(false)
      draftRef.current?.focus()
    }
  }

  const registrarFeedback = async (msgId, valor) => {
    try {
      const data = await enviarFeedback(cursoId, msgId, valor)
      setMensajes((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? {
                ...m,
                feedback_valor: data.feedback_valor,
                feedback_comentario: data.feedback_comentario,
              }
            : m,
        ),
      )
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    }
  }

  const openCite = (msg, chunkIndex, anchor) => {
    const chunk = msg.chunks_usados?.[chunkIndex]
    if (!chunk) return
    setPopover({ index: chunkIndex + 1, chunk, anchor, msgId: msg.id })
  }

  const closeCite = () => setPopover(null)

  return (
    <>
      <Navbar />
      <div style={s.shell} className="chat-shell">
        <ChatSidebar
          cursos={cursos}
          activeId={cursoId}
          onPick={(id) => navigate(`/chat/${id}`)}
          conversaciones={conversaciones}
          conversacionId={conversacionId}
          onSelectConversacion={selectConversacion}
          onNuevoChat={nuevoChat}
        />

        <main style={s.main}>
          {/* Chat header */}
          <header style={s.chatHeader}>
            <TutorBlob size={42} thinking={enviando} mode={modo} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h3
                  style={{
                    fontSize: 16,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  Tutor de {curso?.nombre || '…'}
                </h3>
                {enviando && (
                  <span className="t-mono t-tiny" style={{ color: 'var(--amber-700)' }}>
                    pensando
                    <span className="dots" style={{ marginLeft: 4 }}>
                      <span></span>
                      <span></span>
                      <span></span>
                    </span>
                  </span>
                )}
              </div>
              {curso && (
                <div className="t-tiny t-muted" style={{ marginTop: 2 }}>
                  <span className="t-mono">{curso.codigo}</span>
                  {curso.descripcion && <> · {curso.descripcion}</>}
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => navigate(`/cursos/${cursoId}/quizzes`)}
              className="btn btn-ghost"
              style={{ fontSize: 12.5 }}
              title="Quizzes del curso"
            >
              <Icon name="sparkle" size={13} /> Quizzes
            </button>
            <ModeToggle modo={modo} onChange={setModo} />
          </header>

          {/* Messages */}
          <div ref={scrollRef} style={s.messages}>
            {loadingHist ? (
              <p className="t-muted" style={{ textAlign: 'center', padding: 40 }}>
                Cargando historial…
              </p>
            ) : mensajes.length === 0 && !enviando ? (
              <WelcomeCard onPick={send} modo={modo} suggestions={suggestions} />
            ) : (
              <>
                {mensajes.map((m) => (
                  <MessageGroup
                    key={m.id}
                    msg={m}
                    onCite={openCite}
                    onFeedback={registrarFeedback}
                    activeChunk={popover?.msgId === m.id ? popover.index : null}
                  />
                ))}
              </>
            )}

            {error && (
              <p style={s.error}>
                <Icon name="x" size={14} /> {error}
              </p>
            )}
          </div>

          {/* Composer */}
          <div style={s.composerWrap}>
            <div style={s.suggRow}>
              {suggestions.map((sg) => (
                <button
                  key={sg}
                  type="button"
                  onClick={() => send(sg)}
                  style={s.suggChip}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--amber-100)'
                    e.currentTarget.style.borderColor = 'var(--amber-200)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'var(--paper-2)'
                    e.currentTarget.style.borderColor = 'transparent'
                  }}
                >
                  <Icon name="sparkle" size={11} style={{ color: 'var(--amber-700)' }} />
                  {sg}
                </button>
              ))}
            </div>

            <Composer
              draft={draft}
              setDraft={setDraft}
              onSend={() => send()}
              disabled={enviando || loadingHist}
              inputRef={draftRef}
            />

            <div className="t-faint t-tiny" style={{ marginTop: 8, textAlign: 'center' }}>
              Las respuestas se basan en el material de tu curso. Las{' '}
              <span className="t-mono">[1]</span> son citas clickeables.
            </div>
          </div>
        </main>
      </div>

      {popover && (
        <CitationPopover
          index={popover.index}
          chunk={popover.chunk}
          anchor={popover.anchor}
          onClose={closeCite}
        />
      )}

      <style>{`
        @media (max-width: 880px) {
          .chat-shell { grid-template-columns: 1fr !important; height: auto !important; }
          .chat-shell > .chat-sidebar { display: none; }
        }
      `}</style>
    </>
  )
}

function ModeToggle({ modo, onChange }) {
  const options = [
    { id: 'directo', label: 'Directo', icon: 'bolt' },
    { id: 'socratico', label: 'Socratico', icon: 'target' },
  ]
  return (
    <div style={s.modeToggle} role="group" aria-label="Modo del tutor">
      {options.map((op) => {
        const active = modo === op.id
        const activeStyle =
          active && op.id === 'socratico'
            ? { ...s.modeButtonActive, color: 'var(--lav-700)', borderColor: 'var(--lav-200)' }
            : active
              ? s.modeButtonActive
              : null
        return (
          <button
            key={op.id}
            type="button"
            onClick={() => onChange(op.id)}
            style={{
              ...s.modeButton,
              transition: 'color .3s ease, background .3s ease, border-color .3s ease',
              ...activeStyle,
            }}
            title={op.id === 'socratico' ? 'Guia progresiva' : 'Respuesta directa'}
            aria-pressed={active}
          >
            <Icon name={op.icon} size={13} />
            <span>{op.label}</span>
          </button>
        )
      })}
    </div>
  )
}

function ChatSidebar({
  cursos,
  activeId,
  onPick,
  conversaciones,
  conversacionId,
  onSelectConversacion,
  onNuevoChat,
}) {
  return (
    <aside className="chat-sidebar" style={s.sidebar}>
      <div style={{ padding: '16px 14px 6px' }}>
        <div className="t-eyebrow" style={{ marginBottom: 10 }}>Mis cursos</div>
        {cursos.length === 0 && (
          <p className="t-tiny t-muted">Aún no estás en ningún curso.</p>
        )}
        {cursos.map((c, i) => {
          const color = colorForIndex(i)
          const active = c.id === activeId
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => onPick(c.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                width: '100%',
                padding: '8px 10px',
                background: active ? 'var(--paper-2)' : 'transparent',
                border: '1px solid ' + (active ? 'var(--ink-100)' : 'transparent'),
                borderRadius: 10,
                textAlign: 'left',
                marginBottom: 4,
                cursor: 'pointer',
                color: 'var(--ink-900)',
              }}
            >
              <div
                style={{
                  width: 6,
                  height: 36,
                  borderRadius: 4,
                  background:
                    color === 'amber'
                      ? 'var(--amber-500)'
                      : color === 'mint'
                        ? 'var(--mint-500)'
                        : 'var(--lav-500)',
                  flex: 'none',
                }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="t-mono t-tiny" style={{ color: 'var(--ink-500)' }}>
                  {c.codigo}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: active ? 500 : 400,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {c.nombre}
                </div>
              </div>
            </button>
          )
        })}
      </div>

      <div style={{ borderTop: '1px solid var(--ink-100)', padding: '12px 14px', flex: 1, minHeight: 0, overflowY: 'auto' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 10,
          }}
        >
          <div className="t-eyebrow">Conversaciones</div>
          <button
            type="button"
            onClick={onNuevoChat}
            className="btn btn-soft"
            style={{ fontSize: 11.5, padding: '4px 8px' }}
            title="Empezar una conversación nueva"
          >
            <Icon name="plus" size={12} /> Nuevo
          </button>
        </div>
        {conversaciones.length === 0 ? (
          <p className="t-tiny t-muted">Aún no tienes conversaciones en este curso.</p>
        ) : (
          conversaciones.map((conv) => {
            const active = conv.id === conversacionId
            return (
              <button
                key={conv.id}
                type="button"
                onClick={() => onSelectConversacion(conv.id)}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid ' + (active ? 'var(--amber-200)' : 'transparent'),
                  background: active ? 'var(--amber-100)' : 'transparent',
                  cursor: 'pointer',
                  marginBottom: 2,
                }}
                title={conv.titulo}
              >
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: active ? 500 : 400,
                    color: active ? 'var(--amber-700)' : 'var(--ink-700)',
                    overflow: 'hidden',
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {conv.titulo}
                </div>
              </button>
            )
          })
        )}
      </div>

      <div style={{ marginTop: 'auto', padding: 14, borderTop: '1px solid var(--ink-100)' }}>
        <div
          style={{
            padding: 12,
            background: 'linear-gradient(135deg, var(--mint-100), var(--surface))',
            borderRadius: 12,
            fontSize: 12,
            lineHeight: 1.5,
          }}
        >
          <Icon name="sparkle" size={14} style={{ color: 'var(--mint-700)', marginBottom: 6 }} />
          <div style={{ color: 'var(--ink-700)' }}>
            Tu tutor solo ve el material que tus docentes subieron a este curso.
          </div>
        </div>
      </div>
    </aside>
  )
}

function WelcomeCard({ onPick, modo, suggestions }) {
  return (
    <div className="fade-up" style={{ padding: '20px 0', textAlign: 'center' }}>
      <div style={{ display: 'inline-block' }}>
        <TutorBlob size={72} mode={modo} />
      </div>
      <h2 style={{ marginTop: 14, marginBottom: 6 }}>¿Por dónde empezamos?</h2>
      <p className="t-muted" style={{ marginBottom: 20 }}>
        Pregúntame algo del material y te respondo con citas.
      </p>
      <div
        style={{
          display: 'flex',
          gap: 8,
          justifyContent: 'center',
          flexWrap: 'wrap',
          maxWidth: 600,
          margin: '0 auto',
        }}
      >
        {suggestions.map((sg) => (
          <button
            key={sg}
            type="button"
            onClick={() => onPick(sg)}
            className="btn btn-ghost"
            style={{ fontSize: 13 }}
          >
            {sg}
          </button>
        ))}
      </div>
    </div>
  )
}

function UserBubble({ text, time }) {
  return (
    <div className="fade-up" style={{ display: 'flex', justifyContent: 'flex-end' }}>
      <div
        style={{
          maxWidth: '75%',
          padding: '12px 16px',
          background: 'var(--ink-900)',
          color: 'var(--paper)',
          borderRadius: '18px 18px 4px 18px',
          fontSize: 14.5,
          lineHeight: 1.55,
          whiteSpace: 'pre-wrap',
        }}
      >
        {text}
        {time && (
          <div
            className="t-mono"
            style={{ fontSize: 10.5, opacity: 0.55, marginTop: 4, textAlign: 'right' }}
          >
            {time}
          </div>
        )}
      </div>
    </div>
  )
}

function MessageGroup({ msg, onCite, onFeedback, activeChunk }) {
  const isStreaming = msg.streaming === true
  const time = useMemo(() => {
    if (!msg.creado_en) return null
    try {
      const d = new Date(msg.creado_en)
      return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
    } catch {
      return null
    }
  }, [msg.creado_en])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <UserBubble text={msg.pregunta} time={time} />
      <div className="fade-up" style={{ display: 'flex', gap: 12 }}>
        <TutorBlob size={36} mode={msg.modo} />
        <div style={{ flex: 1, minWidth: 0, maxWidth: 720 }}>
          <div
            style={{
              padding: '14px 18px',
              background: 'var(--surface)',
              border: '1px solid var(--ink-100)',
              borderRadius: '4px 18px 18px 18px',
              fontSize: 15,
              lineHeight: 1.65,
              color: 'var(--ink-900)',
              whiteSpace: 'pre-wrap',
              minHeight: 52,
            }}
          >
            {msg.respuesta ? (
              <>
                {msg.respuesta}
                {isStreaming && <span className="stream-cursor" aria-hidden="true" />}
              </>
            ) : isStreaming ? (
              <span className="stream-waiting">
                {msg.streamStage === 'retrieving' ? 'buscando material' : 'escribiendo'}
                <span className="stream-dots" aria-hidden="true">
                  <span></span>
                  <span></span>
                  <span></span>
                </span>
                <span className="stream-cursor" aria-hidden="true" />
              </span>
            ) : null}
          </div>

          {!isStreaming && msg.chunks_usados?.length > 0 && (() => {
            // Dedup: un mismo documento/página aparece una sola vez.
            // Guardamos el índice original para que onCite abra el fragmento correcto.
            const seen = new Set()
            const uniqueChunks = []
            msg.chunks_usados.forEach((c, i) => {
              const key = `${c.nombre_doc}||${c.pagina}`
              if (!seen.has(key)) {
                seen.add(key)
                uniqueChunks.push({ chunk: c, originalIndex: i })
              }
            })
            return (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  flexWrap: 'wrap',
                  marginTop: 10,
                  paddingLeft: 4,
                }}
              >
                <span className="t-tiny t-muted">Fuentes:</span>
                {uniqueChunks.map(({ chunk: c, originalIndex }, displayIndex) => {
                  const n = displayIndex + 1
                  const active = activeChunk === originalIndex + 1
                  return (
                    <button
                      key={`${msg.id}-${originalIndex}`}
                      type="button"
                      className={`chip chip-amber ${active ? 'cite active' : ''}`}
                      onClick={(e) => {
                        const r = e.currentTarget.getBoundingClientRect()
                        onCite(msg, originalIndex, { x: r.left, y: r.bottom })
                      }}
                      style={{ cursor: 'pointer', maxWidth: 260 }}
                      title={c.nombre_doc}
                    >
                      <span className="t-mono" style={{ fontSize: 10 }}>
                        [{n}]
                      </span>
                      <span
                        style={{
                          overflow: 'hidden',
                          whiteSpace: 'nowrap',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {c.nombre_doc} · pág. {c.pagina ?? '—'}
                      </span>
                    </button>
                  )
                })}
              </div>
            )
          })()}

          {!isStreaming && (
          <div style={s.reactRow}>
            <span className="chip" style={s.modeChip}>
              {msg.modo === 'socratico' ? 'Socratico' : 'Directo'}
            </span>
            <button
              type="button"
              className="reaction"
              onClick={() => onFeedback(msg.id, 'positivo')}
              title="Útil"
              style={msg.feedback_valor === 'positivo' ? s.reactActive : null}
            >
              👍
            </button>
            <button
              type="button"
              className="reaction"
              onClick={() => onFeedback(msg.id, 'negativo')}
              title="A mejorar"
              style={msg.feedback_valor === 'negativo' ? s.reactActive : null}
            >
              👎
            </button>
            <button
              type="button"
              className="reaction"
              onClick={() => navigator.clipboard?.writeText(msg.respuesta || '')}
              title="Copiar"
            >
              ⎘
            </button>
            {time && (
              <span
                className="t-mono t-tiny t-faint"
                style={{ marginLeft: 'auto' }}
              >
                {time}
              </span>
            )}
          </div>
          )}
        </div>
      </div>

      <style>{`
        .reaction {
          background: transparent;
          border: 1px solid var(--ink-100);
          border-radius: 8px;
          padding: 3px 8px;
          cursor: pointer;
          font-size: 13px;
          transition: all .12s ease;
          color: var(--ink-700);
        }
        .reaction:hover { background: var(--paper-2); transform: translateY(-1px); }
        .stream-waiting {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          color: var(--ink-500);
          font-family: var(--font-mono);
          font-size: 12px;
        }
        .stream-dots {
          display: inline-flex;
          align-items: center;
          gap: 3px;
        }
        .stream-dots span {
          width: 4px;
          height: 4px;
          border-radius: 50%;
          background: var(--ink-500);
          opacity: .35;
          animation: stream-dot 1s infinite ease-in-out;
        }
        .stream-dots span:nth-child(2) { animation-delay: .16s; }
        .stream-dots span:nth-child(3) { animation-delay: .32s; }
        .stream-cursor {
          display: inline-block;
          width: 1.5px;
          height: 1.15em;
          margin-left: 2px;
          vertical-align: -0.18em;
          border-radius: 2px;
          background: var(--ink-900);
          animation: stream-blink .86s steps(1, end) infinite;
        }
        @keyframes stream-blink {
          0%, 45% { opacity: 1; }
          46%, 100% { opacity: 0; }
        }
        @keyframes stream-dot {
          0%, 100% { opacity: .25; transform: translateY(0); }
          50% { opacity: .9; transform: translateY(-2px); }
        }
      `}</style>
    </div>
  )
}

function Composer({ draft, setDraft, onSend, disabled, inputRef }) {
  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }
  useEffect(() => {
    if (inputRef?.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 140) + 'px'
    }
  }, [draft, inputRef])

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: 8,
        padding: 8,
        background: 'var(--paper-2)',
        border: '1px solid var(--ink-100)',
        borderRadius: 18,
      }}
    >
      <button
        type="button"
        className="btn btn-ghost"
        style={{ padding: 8, borderRadius: 12 }}
        title="Adjuntar (próximamente)"
        disabled
      >
        <Icon name="paperclip" size={16} />
      </button>
      <textarea
        ref={inputRef}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKey}
        placeholder="Pregúntale al tutor… (Shift+Enter para nueva línea)"
        rows={1}
        disabled={disabled}
        style={{
          flex: 1,
          background: 'transparent',
          border: 'none',
          outline: 'none',
          resize: 'none',
          fontFamily: 'var(--font-body)',
          fontSize: 14.5,
          padding: '9px 4px',
          lineHeight: 1.5,
          maxHeight: 140,
          color: 'var(--ink-900)',
        }}
      />
      <button
        type="button"
        onClick={onSend}
        disabled={!draft.trim() || disabled}
        className="btn btn-primary"
        style={{ padding: '9px 12px' }}
        title="Enviar"
      >
        <Icon name="send" size={15} />
      </button>
    </div>
  )
}

const s = {
  shell: {
    maxWidth: 'var(--maxw)',
    margin: '0 auto',
    padding: '16px 16px 24px',
    display: 'grid',
    gridTemplateColumns: '260px 1fr',
    gap: 16,
    height: 'calc(100vh - var(--nav-h))',
  },
  sidebar: {
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--surface)',
    border: '1px solid var(--ink-100)',
    borderRadius: 'var(--r-xl)',
    overflow: 'hidden',
    boxShadow: 'var(--sh-1)',
  },
  main: {
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--surface)',
    border: '1px solid var(--ink-100)',
    borderRadius: 'var(--r-xl)',
    overflow: 'hidden',
    boxShadow: 'var(--sh-1)',
    minWidth: 0,
  },
  chatHeader: {
    padding: '14px 22px',
    borderBottom: '1px solid var(--ink-100)',
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    background: 'linear-gradient(180deg, rgba(228,238,248,.5), transparent)',
  },
  modeToggle: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 3,
    padding: 3,
    background: 'var(--paper-2)',
    border: '1px solid var(--ink-100)',
    borderRadius: 12,
    flexShrink: 0,
  },
  modeButton: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
    minWidth: 88,
    height: 30,
    padding: '0 9px',
    border: '1px solid transparent',
    borderRadius: 9,
    background: 'transparent',
    color: 'var(--ink-600)',
    fontSize: 12,
    cursor: 'pointer',
  },
  modeButtonActive: {
    background: 'var(--surface)',
    borderColor: 'var(--ink-100)',
    color: 'var(--ink-900)',
    boxShadow: 'var(--sh-1)',
  },
  modeChip: {
    padding: '3px 8px',
    fontSize: 11,
    color: 'var(--ink-500)',
    background: 'var(--paper-2)',
    borderColor: 'var(--ink-100)',
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '26px 22px',
    background: 'var(--paper)',
    display: 'flex',
    flexDirection: 'column',
    gap: 22,
  },
  composerWrap: {
    padding: '14px 22px 18px',
    borderTop: '1px solid var(--ink-100)',
    background: 'var(--surface)',
  },
  suggRow: { display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' },
  suggChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '7px 13px',
    background: 'var(--paper-2)',
    border: '1px solid transparent',
    borderRadius: 'var(--r-pill)',
    fontSize: 12.5,
    color: 'var(--ink-700)',
    cursor: 'pointer',
    transition: 'all .15s ease',
  },
  reactRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginTop: 8,
    paddingLeft: 4,
    color: 'var(--ink-400)',
  },
  reactActive: {
    background: 'var(--amber-100)',
    borderColor: 'var(--amber-500)',
    color: 'var(--amber-700)',
  },
  error: {
    color: 'var(--danger)',
    background: 'rgba(214,90,71,.07)',
    border: '1px solid rgba(214,90,71,.25)',
    borderRadius: 'var(--r-sm)',
    padding: '8px 12px',
    fontSize: 13,
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'center',
  },
}
