import { api } from './client.js'
import { auth } from '../firebase.js'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export const enviarPregunta = (cursoId, pregunta, conversacionId = null, modo = 'directo') =>
  api
    .post(`/cursos/${cursoId}/chat`, {
      pregunta,
      conversacion_id: conversacionId,
      modo,
    })
    .then((r) => r.data)

export async function enviarPreguntaStream(cursoId, pregunta, conversacionId, modo, handlers = {}) {
  const token = await auth.currentUser?.getIdToken()
  const response = await fetch(`${baseURL}/cursos/${cursoId}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      pregunta,
      conversacion_id: conversacionId,
      modo,
    }),
  })

  if (!response.ok || !response.body) {
    const text = await response.text().catch(() => '')
    throw new Error(text || `Error HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatchEvent = (rawEvent) => {
    const lines = rawEvent.split('\n')
    const event = lines
      .find((line) => line.startsWith('event:'))
      ?.slice(6)
      .trim()
    const data = lines
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n')
    if (!event || !data) return

    const payload = JSON.parse(data)
    if (event === 'status') handlers.onStatus?.(payload)
    if (event === 'meta') handlers.onMeta?.(payload)
    if (event === 'delta') handlers.onDelta?.(payload.text || '')
    if (event === 'done') handlers.onDone?.(payload)
    if (event === 'error') {
      const error = new Error(payload.detail || payload.message || 'Error de streaming')
      error.payload = payload
      throw error
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''
    for (const rawEvent of events) {
      dispatchEvent(rawEvent)
    }
  }

  if (buffer.trim()) dispatchEvent(buffer)
}

export const getHistorial = (cursoId, conversacionId = null) =>
  api
    .get(`/cursos/${cursoId}/chat/historial`, {
      params: conversacionId ? { conversacion_id: conversacionId } : undefined,
    })
    .then((r) => r.data)

export const getConversaciones = (cursoId) =>
  api.get(`/cursos/${cursoId}/conversaciones`).then((r) => r.data)

export const enviarFeedback = (cursoId, mensajeId, valor, comentario = null) =>
  api
    .patch(`/cursos/${cursoId}/chat/mensajes/${mensajeId}/feedback`, {
      valor,
      comentario,
    })
    .then((r) => r.data)

export const getAnalytics = (cursoId) =>
  api.get(`/cursos/${cursoId}/analytics`).then((r) => r.data)

export const diagnosticarRag = (cursoId, pregunta) =>
  api.post(`/cursos/${cursoId}/rag/diagnostico`, { pregunta }).then((r) => r.data)
