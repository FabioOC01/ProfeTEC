import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

/**
 * Barra superior compartida entre páginas autenticadas.
 * Props:
 *   - breadcrumb: nodo opcional a mostrar en el centro (ej: "Mis cursos › Algoritmos")
 */
export default function Navbar({ breadcrumb }) {
  const navigate = useNavigate()
  const { profile, firebaseUser, logout } = useAuth()
  const [menuAbierto, setMenuAbierto] = useState(false)

  const handleLogout = async () => {
    setMenuAbierto(false)
    await logout()
    navigate('/login', { replace: true })
  }

  const displayName = profile?.nombre || firebaseUser?.displayName || 'Usuario'
  const inicial = displayName.charAt(0).toUpperCase()

  return (
    <nav style={s.nav}>
      <div style={s.container}>
        {/* Logo */}
        <button
          onClick={() => navigate('/dashboard')}
          style={s.logoBtn}
          title="Ir al dashboard"
        >
          <span style={s.logoMark}>🎓</span>
          <span style={s.logoText}>
            ProfeTEC<span style={s.logoAccent}>.IA</span>
          </span>
        </button>

        {/* Breadcrumb opcional */}
        {breadcrumb && <div style={s.breadcrumb}>{breadcrumb}</div>}

        {/* Usuario */}
        <div style={s.userZona}>
          <button
            onClick={() => setMenuAbierto((v) => !v)}
            style={s.userBtn}
            title={displayName}
          >
            {firebaseUser?.photoURL ? (
              <img src={firebaseUser.photoURL} alt="" style={s.avatar} />
            ) : (
              <span style={s.avatarFallback}>{inicial}</span>
            )}
            <span style={s.userNombre}>{displayName.split(' ')[0]}</span>
            {profile?.rol && (
              <span style={{ ...s.rolBadge, ...(profile.rol === 'docente' ? s.rolDocente : s.rolEstudiante) }}>
                {profile.rol === 'docente' ? '👨‍🏫' : '👨‍🎓'} {profile.rol}
              </span>
            )}
            <span style={s.chevron}>{menuAbierto ? '▲' : '▼'}</span>
          </button>

          {menuAbierto && (
            <>
              <div style={s.menuOverlay} onClick={() => setMenuAbierto(false)} />
              <div style={s.menu}>
                <div style={s.menuHeader}>
                  <strong>{displayName}</strong>
                  <small style={s.menuEmail}>{firebaseUser?.email}</small>
                </div>
                <button
                  onClick={() => { navigate('/dashboard'); setMenuAbierto(false) }}
                  style={s.menuItem}
                >
                  🏠 Dashboard
                </button>
                <button
                  onClick={() => { navigate('/cursos'); setMenuAbierto(false) }}
                  style={s.menuItem}
                >
                  📚 Cursos
                </button>
                <div style={s.menuDivider} />
                <button onClick={handleLogout} style={{ ...s.menuItem, color: 'var(--error)' }}>
                  ⎋ Cerrar sesión
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}

const s = {
  nav: {
    position: 'sticky', top: 0, zIndex: 50,
    background: 'rgba(13, 17, 23, 0.92)',
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
    borderBottom: '1px solid var(--border)',
  },
  container: {
    maxWidth: 1100, margin: '0 auto', padding: '0.75rem 1.5rem',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem',
  },
  logoBtn: {
    display: 'flex', alignItems: 'center', gap: '0.5rem',
    background: 'transparent', border: 'none', padding: 0, cursor: 'pointer',
  },
  logoMark: { fontSize: '1.4rem' },
  logoText: { fontWeight: 700, fontSize: '1.05rem', letterSpacing: '-0.01em', color: 'var(--text)' },
  logoAccent: { color: 'var(--accent)' },
  breadcrumb: {
    flex: 1, textAlign: 'center', fontSize: '0.85rem', color: 'var(--text-dim)',
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  },
  userZona: { position: 'relative' },
  userBtn: {
    display: 'flex', alignItems: 'center', gap: '0.5rem',
    background: 'var(--card)', border: '1px solid var(--border)',
    borderRadius: 99, padding: '0.3rem 0.5rem 0.3rem 0.3rem',
    cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text)',
  },
  avatar: { width: 28, height: 28, borderRadius: '50%' },
  avatarFallback: {
    width: 28, height: 28, borderRadius: '50%',
    background: 'linear-gradient(135deg, #2f81f7, #7c3aed)', color: '#fff',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    fontWeight: 600, fontSize: '0.85rem',
  },
  userNombre: { fontWeight: 500 },
  rolBadge: {
    fontSize: '0.7rem', padding: '0.15rem 0.5rem', borderRadius: 99,
    textTransform: 'capitalize', fontWeight: 500,
  },
  rolDocente: { background: 'rgba(47, 129, 247, 0.18)', color: '#58a6ff' },
  rolEstudiante: { background: 'rgba(63, 185, 80, 0.18)', color: '#56d364' },
  chevron: { fontSize: '0.6rem', color: 'var(--text-dim)' },
  menuOverlay: {
    position: 'fixed', inset: 0, background: 'transparent', zIndex: 40,
  },
  menu: {
    position: 'absolute', top: 'calc(100% + 0.5rem)', right: 0,
    background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10,
    minWidth: 220, padding: '0.4rem', zIndex: 50,
    boxShadow: '0 12px 40px rgba(0, 0, 0, 0.6)',
  },
  menuHeader: {
    padding: '0.6rem 0.75rem', display: 'flex', flexDirection: 'column', gap: '0.15rem',
    borderBottom: '1px solid var(--border)', marginBottom: '0.3rem',
  },
  menuEmail: { color: 'var(--text-dim)', fontSize: '0.72rem' },
  menuItem: {
    display: 'block', width: '100%', textAlign: 'left',
    background: 'transparent', border: 'none', color: 'var(--text)',
    padding: '0.55rem 0.75rem', borderRadius: 6,
    cursor: 'pointer', fontSize: '0.875rem',
  },
  menuDivider: {
    height: 1, background: 'var(--border)', margin: '0.3rem 0',
  },
}
