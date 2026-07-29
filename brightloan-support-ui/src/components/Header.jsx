import { useAuth } from '../context/AuthContext.jsx'
import BrandMark from './BrandMark.jsx'

export default function Header() {
  const { user, logout } = useAuth()
  const firstName = user?.name?.split(' ')[0]

  return (
    <div className="flex items-center justify-between bg-gradient-to-r from-indigo-600 to-blue-600 px-6 py-4">
      <div className="flex items-center gap-3">
        <BrandMark size="sm" />
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-indigo-100">
            Brightloan Support
          </p>
          <p className="text-base font-semibold text-white">Hi {firstName}</p>
        </div>
      </div>
      <button
        onClick={logout}
        className="rounded-full bg-white/10 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-white/20"
      >
        Sign out
      </button>
    </div>
  )
}
