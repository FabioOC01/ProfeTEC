import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { enviarIntento, getQuiz, listarIntentos } from '../../api/quizzes.js'
import { useAuth } from '../../context/AuthContext.jsx'
import Navbar from '../../components/Navbar.jsx'
import Icon from '../../components/ui/Icon.jsx'

export default function QuizDetallePage() {
  const { cursoId, quizId } = useParams()
  const navigate = useNavigate()
  const { profile, viewMode } = useAuth()
  const isDocente = viewMode === 'docente'
  const canSubmit = profile?.rol === 'estudiante' && viewMode === 'estudiante'
  const canSeeAttempts = profile?.rol === 'docente' && viewMode === 'docente'

  const [quiz, setQuiz] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Estudiante
  const [respuestas, setRespuestas] = useState([])
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState(null)

  // Docente
  const [intentos, setIntentos] = useState([])

  useEffect(() => {
    let alive = true
    setLoading(true)
    getQuiz(cursoId, quizId)
      .then((q) => {
        if (!alive) return
        setQuiz(q)
        setRespuestas(new Array(q.preguntas.length).fill(-1))
      })
      .catch((e) => alive && setError(e.response?.data?.detail || e.message))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [cursoId, quizId])

  useEffect(() => {
    if (!canSeeAttempts || !quiz) return
    listarIntentos(cursoId, quizId).then(setIntentos).catch(() => {})
  }, [canSeeAttempts, quiz, cursoId, quizId])

  const onChange = (i, value) => {
    setRespuestas((prev) => {
      const copia = [...prev]
      copia[i] = value
      return copia
    })
  }

  const onEnviar = async () => {
    if (respuestas.some((r) => r < 0)) {
      setError('Debes responder todas las preguntas antes de enviar.')
      return
    }
    setEnviando(true)
    setError(null)
    try {
      const r = await enviarIntento(cursoId, quizId, respuestas)
      setResultado(r)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setEnviando(false)
    }
  }

  if (loading) {
    return (
      <>
        <Navbar />
        <p className="t-muted" style={{ textAlign: 'center', padding: 40 }}>
          Cargando quiz…
        </p>
      </>
    )
  }

  if (!quiz) {
    return (
      <>
        <Navbar />
        <div style={s.shell}>
          <p style={s.error}><Icon name="x" size={14} /> {error || 'Quiz no encontrado.'}</p>
        </div>
      </>
    )
  }

  return (
    <>
      <Navbar />
      <div style={s.shell}>
        <header style={s.header}>
          <div>
            <div className="t-eyebrow" style={{ color: 'var(--lav-700)' }}>Quiz</div>
            <h1 style={{ fontSize: 22, margin: '4px 0 4px' }}>{quiz.titulo}</h1>
            {quiz.tema && (
              <p className="t-tiny t-muted">Tema: {quiz.tema}</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => navigate(`/cursos/${cursoId}/quizzes`)}
            className="btn btn-ghost"
          >
            <Icon name="chevron" size={14} style={{ transform: 'rotate(180deg)' }} /> Volver
          </button>
        </header>

        {error && <p style={s.error}><Icon name="x" size={14} /> {error}</p>}

        {!canSubmit && !isDocente && (
          <p style={s.notice}>
            Estás viendo la experiencia de estudiante en previsualización. Para enviar intentos
            debes tener rol estudiante.
          </p>
        )}

        {isDocente && profile?.rol !== 'docente' && (
          <p style={s.notice}>
            Vista docente en previsualización. Las respuestas correctas solo se muestran si el
            backend las entrega para tu rol real.
          </p>
        )}

        {/* RESULTADO (estudiante) */}
        {resultado && !isDocente && (
          <ResultadoCard
            resultado={resultado}
            quiz={quiz}
            onRepasar={() => navigate(`/chat/${cursoId}`)}
          />
        )}

        {/* PREGUNTAS */}
        {!resultado && (
          <ol style={s.preguntas}>
            {quiz.preguntas.map((p, i) => (
              <li key={i} style={s.pregunta}>
                <div style={s.preguntaHeader}>
                  <span className="t-mono t-tiny t-muted">Pregunta {i + 1}</span>
                  {p.nombre_doc && (
                    <span className="t-tiny t-muted">
                      · {p.nombre_doc}{p.pagina ? `, pág. ${p.pagina}` : ''}
                    </span>
                  )}
                </div>
                <p style={{ marginBottom: 10, fontSize: 15 }}>{p.texto}</p>
                <div style={s.opciones}>
                  {p.opciones.map((opt, j) => {
                    const seleccionada = respuestas[i] === j
                    const esCorrectaDocente = isDocente && j === p.indice_correcto
                    return (
                      <label
                        key={j}
                        style={{
                          ...s.opcion,
                          background: esCorrectaDocente
                            ? 'var(--mint-100)'
                            : seleccionada
                              ? 'var(--amber-100)'
                              : 'var(--paper-2)',
                          borderColor: esCorrectaDocente
                            ? 'var(--mint-500)'
                            : seleccionada
                              ? 'var(--amber-500)'
                              : 'var(--ink-100)',
                        }}
                      >
                        <input
                          type="radio"
                          name={`preg-${i}`}
                          checked={seleccionada}
                          onChange={() => onChange(i, j)}
                          disabled={isDocente}
                          style={{ marginRight: 8 }}
                        />
                        {opt}
                        {esCorrectaDocente && (
                          <span className="t-tiny" style={{ marginLeft: 'auto', color: 'var(--mint-700)' }}>
                            ✓ correcta
                          </span>
                        )}
                      </label>
                    )
                  })}
                </div>
                {isDocente && p.explicacion && (
                  <p className="t-tiny t-muted" style={{ marginTop: 6 }}>
                    <b>Explicación: </b>{p.explicacion}
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}

        {!resultado && !isDocente && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 18 }}>
            <button
              type="button"
              onClick={onEnviar}
              className="btn btn-primary"
              disabled={!canSubmit || enviando || respuestas.some((r) => r < 0)}
              title={canSubmit ? 'Enviar respuestas' : 'Solo disponible para estudiantes reales'}
            >
              {enviando ? 'Enviando…' : 'Enviar respuestas'}
            </button>
          </div>
        )}

        {/* Intentos (docente) */}
        {isDocente && canSeeAttempts && (
          <section style={{ marginTop: 24 }}>
            <h3 style={{ marginBottom: 10 }}>Intentos recibidos ({intentos.length})</h3>
            {intentos.length === 0 ? (
              <p className="t-tiny t-muted">Aún no hay estudiantes que hayan resuelto este quiz.</p>
            ) : (
              <ul style={s.intentosList}>
                {intentos.map((it) => (
                  <li key={it.id} style={s.intentoItem}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14 }}>
                        {it.usuario_nombre || it.usuario_id}
                      </div>
                      <div className="t-tiny t-muted">
                        {new Date(it.completado_en).toLocaleString()}
                      </div>
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>
                      {it.correctas}/{it.total_preguntas}{' '}
                      <span className="t-tiny t-muted">
                        ({Math.round(it.porcentaje * 100)}%)
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
      </div>
    </>
  )
}

function ResultadoCard({ resultado, quiz, onRepasar }) {
  const pct = Math.round(resultado.porcentaje * 100)
  const incorrectas = resultado.detalle.filter((d) => !d.es_correcta)
  const tiempoEstimado = Math.max(5, incorrectas.length * 3 + 4)
  const xp = resultado.correctas * 50
  const mensaje = pct >= 80
    ? 'Excelente dominio del material.'
    : pct >= 50
      ? 'Vas bien, queda ajustar algunos puntos.'
      : 'Hay material por repasar.'
  const temas = incorrectas.slice(0, 3).map((d) => temaCorto(d.texto))

  return (
    <section style={s.resultShell}>
      <div style={s.resultHero}>
        <div style={s.scoreRingWrap}>
          <div
            style={{
              ...s.scoreRing,
              background: `conic-gradient(#ffffff ${pct * 3.6}deg, rgba(255,255,255,.28) 0deg)`,
            }}
          >
            <div style={s.scoreRingInner}>{pct}%</div>
          </div>
        </div>
        <div style={s.resultHeroText}>
          <div className="t-eyebrow" style={s.resultEyebrow}>Quiz entregado</div>
          <h2 style={s.resultTitle}>{mensaje}</h2>
          <p style={s.resultSubtitle}>
            Acertaste {resultado.correctas} de {resultado.total_preguntas}.{' '}
            {incorrectas.length
              ? 'Te recomiendo retomar el material y volver al tutor.'
              : 'Puedes continuar con el siguiente repaso.'}
          </p>
          <div style={s.resultStats}>
            <Metric value={`${tiempoEstimado}m`} label="tiempo" />
            <Metric value={`+${xp}`} label="XP ganado" />
            <Metric value={incorrectas.length ? `${incorrectas.length}` : '0'} label="en duda" />
          </div>
        </div>
      </div>

      <div style={s.reinforce}>
        <div style={s.reinforceIcon}>
          <Icon name={incorrectas.length ? 'target' : 'check'} size={18} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h3 style={s.reinforceTitle}>
            {incorrectas.length
              ? `Vamos a reforzar ${incorrectas.length} ${incorrectas.length === 1 ? 'cosa' : 'cosas'}`
              : 'Todo correcto'}
          </h3>
          <p style={s.reinforceCopy}>
            {incorrectas.length
              ? 'Las preguntas que fallaste tocan los siguientes temas:'
              : 'Buen trabajo. Igual puedes repasar con el tutor para consolidar.'}
          </p>
          <div style={s.topicRow}>
            {(temas.length ? temas : ['Repaso general']).map((tema) => (
              <span key={tema} style={s.topicChip}>{tema}</span>
            ))}
          </div>
        </div>
        <button type="button" className="btn btn-primary" onClick={onRepasar} style={s.reviewButton}>
          Repasar con el tutor <Icon name="arrow" size={13} />
        </button>
      </div>

      <div className="t-eyebrow" style={s.reviewEyebrow}>
        Revisión pregunta por pregunta
      </div>

      <div style={s.reviewList}>
        {resultado.detalle.map((d) => (
          <PreguntaResultado
            key={d.indice_pregunta}
            detalle={d}
            preguntaOriginal={quiz?.preguntas?.[d.indice_pregunta]}
          />
        ))}
      </div>
    </section>
  )
}

function Metric({ value, label }) {
  return (
    <div style={s.resultMetric}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  )
}

function PreguntaResultado({ detalle, preguntaOriginal }) {
  const elegida = detalle.opciones[detalle.elegida] || 'Sin respuesta'
  const correcta = detalle.opciones[detalle.correcta] || ''
  const source = preguntaOriginal?.nombre_doc
    ? `${preguntaOriginal.nombre_doc}${preguntaOriginal.pagina ? ` · pág. ${preguntaOriginal.pagina}` : ''}`
    : null

  return (
    <article style={s.reviewCard}>
      <div style={s.reviewHead}>
        <span
          style={{
            ...s.statusDot,
            background: detalle.es_correcta ? 'var(--mint-100)' : 'rgba(214,90,71,.10)',
            color: detalle.es_correcta ? 'var(--mint-700)' : 'var(--danger)',
          }}
        >
          <Icon name={detalle.es_correcta ? 'check' : 'x'} size={13} />
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="t-mono t-tiny t-muted">
            Pregunta {detalle.indice_pregunta + 1} · Opción múltiple
          </div>
          <h3 style={s.reviewQuestion}>{detalle.texto}</h3>
        </div>
      </div>

      <div style={s.answerStack}>
        <div style={{
          ...s.answerBox,
          background: detalle.es_correcta ? 'var(--mint-100)' : 'rgba(214,90,71,.09)',
          borderColor: detalle.es_correcta ? 'rgba(65,161,122,.22)' : 'rgba(214,90,71,.18)',
        }}>
          <div className="t-eyebrow" style={{
            ...s.answerLabel,
            color: detalle.es_correcta ? 'var(--mint-700)' : 'var(--danger)',
          }}>
            Tu respuesta {detalle.es_correcta ? '(correcta)' : '(incorrecta)'}
          </div>
          <p style={s.answerText}>{elegida}</p>
        </div>

        {!detalle.es_correcta && (
          <div style={{ ...s.answerBox, ...s.correctBox }}>
            <div className="t-eyebrow" style={{ ...s.answerLabel, color: 'var(--mint-700)' }}>
              Respuesta correcta
            </div>
            <p style={s.answerText}>{correcta}</p>
          </div>
        )}

        {detalle.explicacion && (
          <div style={{ ...s.answerBox, ...s.explainBox }}>
            <div className="t-eyebrow" style={{ ...s.answerLabel, color: 'var(--amber-700)' }}>
              Explicación del tutor
            </div>
            <p style={s.explainText}>{detalle.explicacion}</p>
          </div>
        )}
      </div>

      {source && (
        <div style={s.sourceLine}>
          Basado en: <span>{source}</span>
        </div>
      )}
    </article>
  )
}

function temaCorto(texto) {
  return (texto || '')
    .replace(/[¿?]/g, '')
    .split(/\s+/)
    .filter((w) => w.length > 3)
    .slice(0, 4)
    .join(' ')
    || 'Repaso puntual'
}

const s = {
  shell: { maxWidth: 'var(--maxw)', margin: '0 auto', padding: '20px 18px 60px' },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 18,
    flexWrap: 'wrap',
  },
  preguntas: { listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 12 },
  pregunta: {
    background: 'var(--surface)',
    border: '1px solid var(--ink-100)',
    borderRadius: 12,
    padding: 16,
  },
  preguntaHeader: { display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 },
  opciones: { display: 'flex', flexDirection: 'column', gap: 8 },
  opcion: {
    display: 'flex',
    alignItems: 'center',
    padding: '10px 12px',
    border: '1px solid',
    borderRadius: 10,
    cursor: 'pointer',
    fontSize: 14,
    transition: 'all .12s ease',
  },
  card: {
    background: 'var(--surface)',
    border: '1px solid var(--ink-100)',
    borderRadius: 14,
    padding: 18,
    marginBottom: 18,
  },
  resultShell: {
    maxWidth: 960,
    margin: '0 auto 28px',
    display: 'flex',
    flexDirection: 'column',
    gap: 14,
  },
  resultHero: {
    display: 'grid',
    gridTemplateColumns: '94px minmax(0, 1fr)',
    gap: 18,
    alignItems: 'center',
    background: 'linear-gradient(135deg, #4a8fcf 0%, #1f5d9c 100%)',
    borderRadius: 14,
    padding: '22px 24px',
    color: '#fff',
    boxShadow: 'var(--sh-3)',
  },
  scoreRingWrap: {
    display: 'flex',
    justifyContent: 'center',
  },
  scoreRing: {
    width: 74,
    height: 74,
    borderRadius: '50%',
    display: 'grid',
    placeItems: 'center',
  },
  scoreRingInner: {
    width: 58,
    height: 58,
    borderRadius: '50%',
    display: 'grid',
    placeItems: 'center',
    background: 'rgba(255,255,255,.18)',
    color: '#fff',
    fontSize: 22,
    fontWeight: 700,
  },
  resultHeroText: {
    minWidth: 0,
  },
  resultEyebrow: {
    color: 'rgba(255,255,255,.78)',
    marginBottom: 4,
  },
  resultTitle: {
    color: '#fff',
    fontSize: 25,
    marginBottom: 6,
  },
  resultSubtitle: {
    color: 'rgba(255,255,255,.92)',
    fontSize: 13,
    maxWidth: 580,
  },
  resultStats: {
    display: 'flex',
    gap: 24,
    flexWrap: 'wrap',
    marginTop: 14,
  },
  resultMetric: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
    color: '#fff',
    minWidth: 58,
  },
  reinforce: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    flexWrap: 'wrap',
    background: 'linear-gradient(180deg, #e1f2ea 0%, #d7eee3 100%)',
    border: '1px solid rgba(65,161,122,.32)',
    borderRadius: 12,
    padding: '13px 16px',
    boxShadow: 'var(--sh-1)',
  },
  reinforceIcon: {
    width: 34,
    height: 34,
    borderRadius: '50%',
    display: 'grid',
    placeItems: 'center',
    background: 'rgba(255,255,255,.62)',
    color: 'var(--mint-700)',
    flex: 'none',
  },
  reinforceTitle: {
    fontSize: 15,
    marginBottom: 2,
  },
  reinforceCopy: {
    fontSize: 12,
    color: 'var(--ink-700)',
  },
  topicRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 9,
  },
  topicChip: {
    fontSize: 11,
    color: 'var(--ink-700)',
    background: 'rgba(255,255,255,.45)',
    border: '1px solid rgba(65,161,122,.18)',
    borderRadius: 999,
    padding: '4px 9px',
  },
  reviewButton: {
    fontSize: 12,
    padding: '8px 13px',
    alignSelf: 'center',
  },
  reviewEyebrow: {
    color: 'var(--ink-500)',
    margin: '4px 0 2px',
  },
  reviewList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  reviewCard: {
    background: 'var(--surface)',
    border: '1px solid var(--ink-100)',
    borderRadius: 12,
    padding: 14,
    boxShadow: 'var(--sh-1)',
  },
  reviewHead: {
    display: 'flex',
    gap: 10,
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  statusDot: {
    width: 26,
    height: 26,
    borderRadius: 8,
    display: 'grid',
    placeItems: 'center',
    flex: 'none',
  },
  reviewQuestion: {
    fontSize: 14,
    lineHeight: 1.35,
    marginTop: 3,
  },
  answerStack: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  answerBox: {
    border: '1px solid',
    borderRadius: 8,
    padding: '10px 12px',
  },
  correctBox: {
    background: 'var(--mint-100)',
    borderColor: 'rgba(65,161,122,.22)',
  },
  explainBox: {
    background: 'var(--amber-100)',
    borderColor: 'rgba(74,143,207,.18)',
  },
  answerLabel: {
    letterSpacing: '0.11em',
    marginBottom: 4,
  },
  answerText: {
    fontSize: 13,
    color: 'var(--ink-900)',
    fontWeight: 500,
  },
  explainText: {
    fontSize: 12.5,
    color: 'var(--ink-700)',
  },
  sourceLine: {
    marginTop: 9,
    fontSize: 11,
    color: 'var(--ink-500)',
  },
  intentosList: {
    listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 6,
  },
  intentoItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 14px',
    background: 'var(--paper-2)',
    border: '1px solid var(--ink-100)',
    borderRadius: 10,
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
  notice: {
    color: 'var(--amber-700)',
    background: 'var(--amber-100)',
    border: '1px solid var(--amber-200)',
    borderRadius: 'var(--r-sm)',
    padding: '8px 12px',
    fontSize: 13,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    marginBottom: 12,
  },
}
