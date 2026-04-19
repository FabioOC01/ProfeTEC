import axios from 'axios'
import { auth } from '../firebase.js'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export const api = axios.create({ baseURL, timeout: 10000 })

// Inyecta el Firebase ID token en cada request
api.interceptors.request.use(async (config) => {
  const user = auth.currentUser
  if (user) {
    const token = await user.getIdToken()
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Redirige al login en 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) window.location.href = '/login'
    return Promise.reject(err)
  },
)

export async function fetchHealth() {
  const { data } = await api.get('/health')
  return data
}
