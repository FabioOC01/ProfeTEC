import { api } from './client.js'

export const enviarPregunta = (cursoId, pregunta, conversacionId = null) =>
  api
    .post(`/cursos/${cursoId}/chat`, {
      pregunta,
      conversacion_id: conversacionId,
    })
    .then((r) => r.data)

export const getHistorial = (cursoId) =>
  api.get(`/cursos/${cursoId}/chat/historial`).then((r) => r.data)
