import { GoogleOAuthProvider } from '@react-oauth/google'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
import SignInScreen from './components/SignInScreen.jsx'
import ChatLayout from './components/ChatLayout.jsx'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

function AppShell() {
  const { user } = useAuth()
  return user ? <ChatLayout /> : <SignInScreen />
}

// Google OAuth is optional until VITE_GOOGLE_CLIENT_ID is set. Without it,
// SignInScreen falls back to a local dev sign-in — see AuthContext.jsx's
// loginAsGuest. Skipping the provider entirely avoids it erroring on an
// empty client ID.
function Providers({ children }) {
  if (!GOOGLE_CLIENT_ID) return children
  return <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>{children}</GoogleOAuthProvider>
}

export default function App() {
  return (
    <Providers>
      <AuthProvider>
        <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-sky-50 p-4">
          <AppShell />
        </div>
      </AuthProvider>
    </Providers>
  )
}
