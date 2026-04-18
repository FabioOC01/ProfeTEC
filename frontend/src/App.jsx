import { useEffect, useState } from 'react'
import { fetchHealth } from './api/client.js'

export default function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <main style={styles.main}>
      <div style={styles.card}>
        <h1 style={styles.title}>ProfeTEC.IA</h1>
        <p style={styles.subtitle}>Sprint 0 — Bootstrap</p>

        <section style={styles.section}>
          <h2 style={styles.h2}>Conexión con backend</h2>
          {loading && <p style={styles.dim}>Verificando /health…</p>}
          {error && (
            <p style={styles.error}>
              Error: {error}
              <br />
              <span style={styles.dim}>
                ¿Está corriendo el backend en{' '}
                {import.meta.env.VITE_API_URL || 'http://localhost:8080'}?
              </span>
            </p>
          )}
          {health && (
            <pre style={styles.pre}>{JSON.stringify(health, null, 2)}</pre>
          )}
        </section>

        <footer style={styles.footer}>
          Tesis — Orlando Fabio Ochoa Cuenca · TECSUP
        </footer>
      </div>
    </main>
  )
}

const styles = {
  main: {
    minHeight: '100vh',
    display: 'grid',
    placeItems: 'center',
    padding: '2rem',
  },
  card: {
    width: '100%',
    maxWidth: 640,
    background: 'var(--card)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: '2rem',
    boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
  },
  title: { margin: 0, fontSize: '2rem', letterSpacing: '-0.02em' },
  subtitle: { margin: '0.25rem 0 1.5rem', color: 'var(--text-dim)' },
  section: { marginTop: '1rem' },
  h2: { fontSize: '1rem', textTransform: 'uppercase', color: 'var(--text-dim)', letterSpacing: '0.08em' },
  pre: {
    background: '#0a0d12',
    border: '1px solid var(--border)',
    borderRadius: 8,
    padding: '1rem',
    overflow: 'auto',
    fontSize: '0.875rem',
    color: 'var(--ok)',
  },
  error: { color: 'var(--error)' },
  dim: { color: 'var(--text-dim)' },
  footer: {
    marginTop: '2rem',
    paddingTop: '1rem',
    borderTop: '1px solid var(--border)',
    fontSize: '0.8rem',
    color: 'var(--text-dim)',
  },
}
