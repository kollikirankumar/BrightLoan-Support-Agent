import { createContext, useContext, useState, useCallback } from 'react'
import { api } from '../api/client.js'
import { clearStoredMessages } from '../hooks/useChat.js'

const AuthContext = createContext(null)

const STORAGE_KEY = 'brightloan_user'

function loadStoredUser() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function persistUser(user) {
  try {
    if (user) localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // localStorage unavailable (e.g. private browsing) — session just
    // won't survive a refresh; not worth failing sign-in over.
  }
}

export function AuthProvider({ children }) {
  // Initialized from localStorage so a page refresh doesn't sign the
  // user out — real session/auth (server-verified cookie) lands per
  // 02-frontend-react-auth.md; this is the client-side equivalent for
  // the current dev-mode sign-in.
  const [user, setUser] = useState(loadStoredUser)
  const [authError, setAuthError] = useState(null)

  // Backend re-verifies the Google ID token server-side before creating
  // a session — the frontend never trusts the token's claims directly.
  const loginWithGoogle = useCallback(async (idToken) => {
    setAuthError(null)
    try {
      const { name, email } = await api.googleAuth(idToken)
      const nextUser = { name, email }
      setUser(nextUser)
      persistUser(nextUser)
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
    const nextUser = { name, phone: phone || null, email: email || null }
    setUser(nextUser)
    persistUser(nextUser)
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } catch {
      // no backend to call yet in dev mode — clearing local state is enough
    } finally {
      setUser(null)
      persistUser(null)
      clearStoredMessages()
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
