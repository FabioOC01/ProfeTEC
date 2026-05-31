import { api } from './client.js'

export const crearQuiz = (
  cursoId,
  { titulo, tema, num_preguntas = 5, semana_desde = null, semana_hasta = null },
) =>
  api
    .post(`/cursos/${cursoId}/quizzes`, {
      titulo,
      tema: tema || null,
      num_preguntas,
      semana_desde,
      semana_hasta,
    })
    .then((r) => r.data)

export const listarQuizzes = (cursoId) =>
  api.get(`/cursos/${cursoId}/quizzes`).then((r) => r.data)

export const getQuiz = (cursoId, quizId) =>
  api.get(`/cursos/${cursoId}/quizzes/${quizId}`).then((r) => r.data)

export const eliminarQuiz = (cursoId, quizId) =>
  api.delete(`/cursos/${cursoId}/quizzes/${quizId}`).then((r) => r.data)

export const enviarIntento = (cursoId, quizId, respuestas) =>
  api
    .post(`/cursos/${cursoId}/quizzes/${quizId}/intentos`, { respuestas })
    .then((r) => r.data)

export const listarIntentos = (cursoId, quizId) =>
  api.get(`/cursos/${cursoId}/quizzes/${quizId}/intentos`).then((r) => r.data)
