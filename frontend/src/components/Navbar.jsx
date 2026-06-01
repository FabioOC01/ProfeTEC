import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import Icon from './ui/Icon.jsx'

export default function Navbar({ breadcrumb }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { profile, viewMode, setViewMode, firebaseUser, logout } = useAuth()
  const [menuAbierto, setMenuAbierto] = useState(false)

  const displayName = profile?.nombre || firebaseUser?.displayName || 'Usuario'
  const firstName = displayName.split(' ')[0]
  const inicial = displayName.charAt(0).toUpperCase()
  const realRole = profile?.rol
  const isDocente = viewMode === 'docente'
  const isPreview = realRole && viewMode && realRole !== viewMode

  const handleLogout = async () => {
    setMenuAbierto(false)
    await logout()
    navigate('/login', { replace: true })
  }

  const items = [
    { id: 'dashboard', label: 'Inicio',   icon: 'home', path: '/dashboard' },
    { id: 'cursos',    label: 'Cursos',   icon: 'book', path: '/cursos' },
    { id: 'chat',      label: 'Tutor',    icon: 'chat', path: '/cursos', match: '/chat' },
  ]

  function isActive(it) {
    if (it.match && location.pathname.startsWith(it.match)) return true
    if (it.id === 'dashboard') return location.pathname === '/dashboard'
    if (it.id === 'cursos')
      return location.pathname === '/cursos' || location.pathname.startsWith('/cursos/')
    return location.pathname.startsWith(it.path)
  }

  return (
    <header style={s.nav}>
      <div style={s.container}>
        {/* Logo */}
        <button
          type="button"
          onClick={() => navigate('/dashboard')}
          style={s.logoBtn}
          title="Ir al inicio"
        >
          <img src="/logo.png" alt="ProfeTEC" style={s.logoImg} />
          <div style={s.logoText}>
            <span style={s.logoBrand}>ProfeTEC</span>
          </div>
        </button>

        {/* Nav items */}
        <nav style={s.navItems} className="nav-items">
          {items.map((it) => {
            const active = isActive(it)
            return (
              <button
                key={it.id}
                type="button"
                onClick={() => navigate(it.path)}
                style={{
                  ...s.navBtn,
                  background: active ? 'var(--ink-900)' : 'transparent',
                  color: active ? 'var(--paper)' : 'var(--ink-700)',
                }}
              >
                <Icon name={it.icon} size={16} />
                <span className="nav-label">{it.label}</span>
              </button>
            )
          })}
        </nav>

        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', minWidth: 0 }}>
          {breadcrumb && <div style={s.breadcrumb}>{breadcrumb}</div>}
        </div>

        {/* Right */}
        <div style={s.right}>
          {realRole && (
            <span
              className={isDocente ? 'chip chip-lav' : 'chip chip-mint'}
              style={s.rolChip}
            >
              Vista {isDocente ? 'docente' : 'estudiante'}
            </span>
          )}

          {realRole && (
            <div style={s.viewToggle} role="group" aria-label="Cambiar vista">
              <button
                type="button"
                onClick={() => setViewMode('estudiante')}
                style={{
                  ...s.viewToggleBtn,
                  ...(viewMode === 'estudiante' ? s.viewToggleActive : null),
                }}
                title="Ver como estudiante"
              >
                Est.
              </button>
              <button
                type="button"
                onClick={() => setViewMode('docente')}
                style={{
                  ...s.viewToggleBtn,
                  ...(viewMode === 'docente' ? s.viewToggleActive : null),
                }}
                title="Ver como docente"
              >
                Doc.
              </button>
            </div>
          )}

          <div style={s.userZona}>
            <button
              type="button"
              onClick={() => setMenuAbierto((v) => !v)}
              style={s.userBtn}
              title={displayName}
            >
              {firebaseUser?.photoURL ? (
                <img src={firebaseUser.photoURL} alt="" style={s.avatar} />
              ) : (
                <span style={s.avatarFallback}>{inicial}</span>
              )}
              <span style={s.userNombre}>{firstName}</span>
            </button>

            {menuAbierto && (
              <>
                <div style={s.menuOverlay} onClick={() => setMenuAbierto(false)} />
                <div style={s.menu}>
                  <div style={s.menuHeader}>
                    <strong style={{ fontSize: 14 }}>{displayName}</strong>
                    <small style={s.menuEmail}>{firebaseUser?.email}</small>
                    {isPreview && (
                      <small style={s.menuPreview}>
                        Rol real: {realRole}. Vista activa: {viewMode}.
                      </small>
                    )}
                  </div>
                  <div style={s.menuViewBlock}>
                    <span className="t-tiny t-muted">Cambiar vista</span>
                    <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                      <button
                        type="button"
                        onClick={() => setViewMode('estudiante')}
                        style={{
                          ...s.menuViewBtn,
                          ...(viewMode === 'estudiante' ? s.menuViewBtnActive : null),
                        }}
                      >
                        Estudiante
                      </button>
                      <button
                        type="button"
                        onClick={() => setViewMode('docente')}
                        style={{
                          ...s.menuViewBtn,
                          ...(viewMode === 'docente' ? s.menuViewBtnActive : null),
                        }}
                      >
                        Docente
                      </button>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      navigate('/dashboard')
                      setMenuAbierto(false)
                    }}
                    style={s.menuItem}
                  >
                    <Icon name="home" size={15} /> Inicio
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      navigate('/cursos')
                      setMenuAbierto(false)
                    }}
                    style={s.menuItem}
                  >
                    <Icon name="book" size={15} /> Cursos
                  </button>
                  <div style={s.menuDivider} />
                  <button
                    type="button"
                    onClick={handleLogout}
                    style={{ ...s.menuItem, color: 'var(--danger)' }}
                  >
                    <Icon name="logout" size={15} /> Cerrar sesión
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 760px) {
          .nav-items .nav-label { display: none; }
        }
      `}</style>
    </header>
  )
}

const s = {
  nav: {
    position: 'sticky',
    top: 0,
    zIndex: 40,
    height: 'var(--nav-h)',
    background: 'rgba(250, 246, 240, .82)',
    backdropFilter: 'blur(14px)',
    WebkitBackdropFilter: 'blur(14px)',
    borderBottom: '1px solid var(--ink-100)',
  },
  container: {
    maxWidth: 'var(--maxw)',
    height: '100%',
    margin: '0 auto',
    padding: '0 24px',
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  logoBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    background: 'transparent',
    border: 'none',
    padding: 0,
    cursor: 'pointer',
  },
  logoImg: {
    width: 34,
    height: 34,
    objectFit: 'contain',
    display: 'block',
  },
  logoText: { display: 'flex', flexDirection: 'column', lineHeight: 1, alignItems: 'flex-start' },
  logoBrand: {
    fontFamily: 'var(--font-display)',
    fontWeight: 600,
    fontSize: 17,
    letterSpacing: '-0.02em',
    color: 'var(--ink-900)',
  },
  logoSub: {
    fontFamily: 'var(--font-mono)',
    fontSize: 9,
    color: 'var(--ink-500)',
    letterSpacing: '.15em',
    marginTop: 2,
  },
  navItems: { display: 'flex', gap: 4, marginLeft: 16 },
  navBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 7,
    padding: '8px 14px',
    borderRadius: 'var(--r-pill)',
    border: 'none',
    fontSize: 14,
    fontWeight: 500,
    transition: 'background .15s ease, color .15s ease',
  },
  right: { display: 'flex', alignItems: 'center', gap: 10 },
  rolChip: { textTransform: 'capitalize' },
  viewToggle: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 2,
    padding: 3,
    background: 'var(--paper-2)',
    border: '1px solid var(--ink-100)',
    borderRadius: 'var(--r-pill)',
  },
  viewToggleBtn: {
    height: 26,
    minWidth: 40,
    border: '1px solid transparent',
    borderRadius: 'var(--r-pill)',
    background: 'transparent',
    color: 'var(--ink-600)',
    fontSize: 11.5,
    cursor: 'pointer',
  },
  viewToggleActive: {
    background: 'var(--surface)',
    borderColor: 'var(--ink-100)',
    color: 'var(--ink-900)',
    boxShadow: 'var(--sh-1)',
  },
  userZona: { position: 'relative' },
  userBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '5px 12px 5px 5px',
    background: 'var(--surface)',
    border: '1px solid var(--ink-100)',
    borderRadius: 'var(--r-pill)',
    cursor: 'pointer',
    color: 'var(--ink-900)',
    fontSize: 13,
  },
  avatar: { width: 28, height: 28, borderRadius: '50%' },
  avatarFallback: {
    width: 28,
    height: 28,
    borderRadius: '50%',
    background: 'linear-gradient(135deg, var(--lav-500), var(--amber-500))',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#fff',
    fontWeight: 600,
    fontSize: 13,
  },
  userNombre: { fontWeight: 500 },
  menuOverlay: {
    position: 'fixed',
    inset: 0,
    background: 'transparent',
    zIndex: 40,
  },
  menu: {
    position: 'absolute',
    top: 'calc(100% + 8px)',
    right: 0,
    background: 'var(--surface)',
    border: '1px solid var(--ink-100)',
    borderRadius: 'var(--r-md)',
    minWidth: 240,
    padding: 6,
    zIndex: 50,
    boxShadow: 'var(--sh-pop)',
  },
  menuHeader: {
    padding: '10px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    borderBottom: '1px solid var(--ink-100)',
    marginBottom: 4,
  },
  menuEmail: { color: 'var(--ink-500)', fontSize: 12 },
  menuPreview: { color: 'var(--amber-700)', fontSize: 11.5, marginTop: 4 },
  menuViewBlock: {
    padding: '9px 12px 10px',
    borderBottom: '1px solid var(--ink-100)',
    marginBottom: 4,
  },
  menuViewBtn: {
    flex: 1,
    border: '1px solid var(--ink-100)',
    borderRadius: 'var(--r-sm)',
    background: 'var(--paper-2)',
    padding: '7px 8px',
    fontSize: 12,
    cursor: 'pointer',
    color: 'var(--ink-700)',
  },
  menuViewBtnActive: {
    background: 'var(--ink-900)',
    color: 'var(--paper)',
    borderColor: 'var(--ink-900)',
  },
  menuItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    width: '100%',
    textAlign: 'left',
    background: 'transparent',
    border: 'none',
    color: 'var(--ink-900)',
    padding: '9px 12px',
    borderRadius: 'var(--r-sm)',
    cursor: 'pointer',
    fontSize: 14,
  },
  menuDivider: { height: 1, background: 'var(--ink-100)', margin: '4px 0' },
  breadcrumb: {
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
    color: 'var(--ink-500)',
    letterSpacing: '.04em',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    maxWidth: '100%',
  },
}
