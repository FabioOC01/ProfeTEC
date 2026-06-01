import { createContext, useContext, useEffect, useState } from 'react'
import { onAuthStateChanged, signInWithPopup, signOut } from 'firebase/auth'
import { auth, googleProvider } from '../firebase.js'
import { api } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [firebaseUser, setFirebaseUser] = useState(null)
  const [profile, setProfile] = useState(null)      // perfil Firestore (con rol)
  const [viewMode, setViewModeState] = useState(() => {
    const saved = localStorage.getItem('profetec-view-mode')
    return saved === 'docente' || saved === 'estudiante' ? saved : null
  })
  const [needsOnboarding, setNeedsOnboarding] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, async (user) => {
      setFirebaseUser(user)
      if (user) {
        try {
          const token = await user.getIdToken()
          const { data } = await api.post(
            '/auth/me',
            {},
            { headers: { Authorization: `Bearer ${token}` } },
          )
          setProfile(data.usuario)
          setViewModeState((current) => current || data.usuario?.rol || null)
          setNeedsOnboarding(data.needs_onboarding)
        } catch {
          setProfile(null)
        }
      } else {
        setProfile(null)
        setViewModeState(null)
        setNeedsOnboarding(false)
      }
      setLoading(false)
    })
    return unsub
  }, [])

  const loginWithGoogle = () => signInWithPopup(auth, googleProvider)

  const logout = async () => {
    await signOut(auth)
    setProfile(null)
    setViewModeState(null)
    localStorage.removeItem('profetec-view-mode')
    setNeedsOnboarding(false)
  }

  const setRol = async (rol) => {
    const { data } = await api.patch('/auth/me/rol', { rol })
    setProfile(data.usuario)
    setViewMode(rol)
    setNeedsOnboarding(false)
  }

  const setViewMode = (mode) => {
    const normalized = mode === 'docente' ? 'docente' : 'estudiante'
    localStorage.setItem('profetec-view-mode', normalized)
    setViewModeState(normalized)
  }

  const activeRole = viewMode || profile?.rol || null

  return (
    <AuthContext.Provider
      value={{
        firebaseUser,
        profile,
        viewMode: activeRole,
        setViewMode,
        needsOnboarding,
        loading,
        loginWithGoogle,
        logout,
        setRol,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
