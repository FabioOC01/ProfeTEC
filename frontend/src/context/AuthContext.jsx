import { createContext, useContext, useEffect, useState } from 'react'
import { onAuthStateChanged, signInWithPopup, signOut } from 'firebase/auth'
import { auth, googleProvider } from '../firebase.js'
import { api } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [firebaseUser, setFirebaseUser] = useState(null)
  const [profile, setProfile] = useState(null)      // perfil Firestore (con rol)
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
          setNeedsOnboarding(data.needs_onboarding)
        } catch {
          setProfile(null)
        }
      } else {
        setProfile(null)
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
    setNeedsOnboarding(false)
  }

  const setRol = async (rol) => {
    const { data } = await api.patch('/auth/me/rol', { rol })
    setProfile(data.usuario)
    setNeedsOnboarding(false)
  }

  return (
    <AuthContext.Provider
      value={{ firebaseUser, profile, needsOnboarding, loading, loginWithGoogle, logout, setRol }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
