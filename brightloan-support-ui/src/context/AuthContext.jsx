import { createContext, useContext, useState, useCallback } from 'react'
import { api } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [authError, setAuthError] = useState(null)

  // Backend re-verifies the Google ID token server-side before creating
  // a session — the frontend never trusts the token's claims directly.
  const loginWithGoogle = useCallback(async (idToken) => {
    setAuthError(null)
    try {
      const { name, email } = await api.googleAuth(idToken)
      setUser({ name, email })
    } catch (err) {
      setAuthError('Sign-in failed. Please try again.')
      console.error(err)
    }
  }, [])

  // Local dev fallback used while Google OAuth isn't configured (no
  // VITE_GOOGLE_CLIENT_ID) and/or no backend exists yet to verify a real
  // session against. Sets the user client-side only, no network call.
  // Swap SignInScreen back to Google-only once both are wired up.
  const loginAsGuest = useCallback(({ name, phone, email }) => {
    setAuthError(null)
    setUser({ name, phone: phone || null, email: email || null })
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } catch {
      // no backend to call yet in dev mode — clearing local state is enough
    } finally {
      setUser(null)
    }
  }, [])

  return (
    <AuthContext.Provider
      value={{ user, authError, loginWithGoogle, loginAsGuest, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
