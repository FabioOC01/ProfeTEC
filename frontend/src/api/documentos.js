import { api } from './client.js'

export const getDocumentos = (cursoId) =>
  api.get(`/cursos/${cursoId}/documentos`).then((r) => r.data)

export const uploadDocumento = (cursoId, file, metadata = {}, onProgress) => {
  const form = new FormData()
  form.append('archivo', file)
  form.append('titulo', metadata.titulo)
  form.append('semana', String(metadata.semana))
  if (metadata.referencia) form.append('referencia', metadata.referencia)
  return api.post(`/cursos/${cursoId}/documentos`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total))
    },
  }).then((r) => r.data)
}

export const deleteDocumento = (cursoId, docId) =>
  api.delete(`/cursos/${cursoId}/documentos/${docId}`)
