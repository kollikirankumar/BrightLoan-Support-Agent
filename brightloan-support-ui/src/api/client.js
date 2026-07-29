const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include', // sends the httpOnly session cookie set by /auth/google
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`API error ${res.status}: ${body}`)
  }
  return res.json()
}

// Mirrors the API contract in 02-frontend-react-auth.md
export const api = {
  googleAuth: (idToken) =>
    request('/auth/google', { method: 'POST', body: JSON.stringify({ id_token: idToken }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  getHistory: () => request('/chat/history'),
  sendMessage: (message, userName, phoneNumber, chatHistory) =>
    request('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        user_name: userName,
        phone_number: phoneNumber,
        chat_history: chatHistory || [],
      }),
    }),
}
