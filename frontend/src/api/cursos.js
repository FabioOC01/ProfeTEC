import { api } from './client.js'

export const getCursos = () => api.get('/cursos').then((r) => r.data)
export const getCurso = (id) => api.get(`/cursos/${id}`).then((r) => r.data)
export const createCurso = (body) => api.post('/cursos', body).then((r) => r.data)
export const inscribirCurso = (codigo) => api.post('/cursos/inscribir', { codigo }).then((r) => r.data)
export const updateCurso = (id, body) => api.patch(`/cursos/${id}`, body).then((r) => r.data)
export const deleteCurso = (id) => api.delete(`/cursos/${id}`)
