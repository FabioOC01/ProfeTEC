import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export const api = axios.create({
  baseURL,
  timeout: 10000,
})

export async function fetchHealth() {
  const { data } = await api.get('/health')
  return data
}
