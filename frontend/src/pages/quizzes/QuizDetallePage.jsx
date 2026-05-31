import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { enviarIntento, getQuiz, listarIntentos } from '../../api/quizzes.js'
import { useAuth } from '../../context/AuthContext.jsx'
import Navbar from '../../components/Navbar.jsx'
import Icon from '../../components/ui/Icon.jsx'

export default function QuizDetallePage() {
  const { cursoId, quizId } = useParams()
  const navigate = useNavigate()
  const { profile } = useAuth()
  const isDocente = profile?.rol === 'docente'

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
    if (!isDocente || !quiz) return
    listarIntentos(cursoId, quizId).then(setIntentos).catch(() => {})
  }, [isDocente, quiz, cursoId, quizId])

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

        {/* RESULTADO (estudiante) */}
        {resultado && !isDocente && (
          <ResultadoCard resultado={resultado} />
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
              disabled={enviando || respuestas.some((r) => r < 0)}
            >
              {enviando ? 'Enviando…' : 'Enviar respuestas'}
            </button>
          </div>
        )}

        {/* Intentos (docente) */}
        {isDocente && (
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

function ResultadoCard({ resultado }) {
  const pct = Math.round(resultado.porcentaje * 100)
  return (
    <div style={s.card}>
      <h2 style={{ marginBottom: 6 }}>Resultado: {resultado.correctas}/{resultado.total_preguntas}</h2>
      <p className="t-muted">{pct}% de aciertos</p>
      <ol style={{ marginTop: 16, paddingLeft: 20 }}>
        {resultado.detalle.map((d) => (
          <li key={d.indice_pregunta} style={{ marginBottom: 12 }}>
            <p style={{ marginBottom: 4 }}>{d.texto}</p>
            <p className="t-tiny" style={{ color: d.es_correcta ? 'var(--mint-700)' : 'var(--danger)' }}>
              Tu respuesta: <b>{d.opciones[d.elegida]}</b> {d.es_correcta ? '✓' : '✗'}
            </p>
            {!d.es_correcta && (
              <p className="t-tiny t-muted">
                Respuesta correcta: <b>{d.opciones[d.correcta]}</b>
              </p>
            )}
            {d.explicacion && (
              <p className="t-tiny t-muted" style={{ marginTop: 2 }}>
                {d.explicacion}
              </p>
            )}
          </li>
        ))}
      </ol>
    </div>
  )
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
}
