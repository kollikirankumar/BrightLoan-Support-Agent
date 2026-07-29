import { useState } from 'react'
import { GoogleLogin } from '@react-oauth/google'
import { useAuth } from '../context/AuthContext.jsx'
import BrandMark from './BrandMark.jsx'

// Google sign-in only renders once VITE_GOOGLE_CLIENT_ID is set (see
// .env.example). Until then this falls back to a local dev sign-in so the
// rest of the app is testable without setting up OAuth credentials.
const GOOGLE_ENABLED = Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID)

const PHONE_PATTERN = '[0-9]{10}'

export default function SignInScreen() {
  const { loginWithGoogle, loginAsGuest, authError } = useAuth()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')

  function handleGuestSubmit(e) {
    e.preventDefault()
    if (!name.trim() || !phone.trim()) return
    loginAsGuest({ name: name.trim(), phone: phone.trim() })
  }

  return (
    <div className="w-full max-w-sm rounded-3xl bg-white p-8 text-center shadow-xl shadow-indigo-100 ring-1 ring-slate-100">
      <div className="mb-4 flex justify-center">
        <BrandMark />
      </div>
      <h1 className="mb-1 text-2xl font-bold text-slate-800">Brightloan Support</h1>
      <p className="mb-6 text-sm text-slate-500">
        Sign in to ask about the loan process, offer amounts, or policy — or
        connect with our team.
      </p>

      {GOOGLE_ENABLED ? (
        <div className="flex justify-center">
          <GoogleLogin
            onSuccess={(credentialResponse) => loginWithGoogle(credentialResponse.credential)}
            onError={() => console.error('Google sign-in failed')}
          />
        </div>
      ) : (
        <form onSubmit={handleGuestSubmit} className="space-y-3 text-left">
          <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-700 ring-1 ring-amber-100">
            Google sign-in isn't configured yet. Using local dev sign-in —
            enter your details to continue.
          </p>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            autoFocus
            className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
          <input
            type="tel"
            inputMode="numeric"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Phone number"
            pattern={PHONE_PATTERN}
            title="10-digit phone number"
            className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
          <p className="text-xs text-slate-400">
            Only shared with our team if you ask to speak with someone.
          </p>
          <button
            type="submit"
            disabled={!name.trim() || !phone.trim()}
            className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-md shadow-indigo-200 transition hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
          >
            Continue
          </button>
        </form>
      )}

      {authError && <p className="mt-4 text-sm text-red-600">{authError}</p>}
    </div>
  )
}
