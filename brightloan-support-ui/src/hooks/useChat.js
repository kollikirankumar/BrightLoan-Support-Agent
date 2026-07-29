import { useState, useCallback, useRef, useEffect } from 'react'
import { api } from '../api/client.js'

const HISTORY_MESSAGES = 10 // last ~5 turns (user + assistant pairs)
const MESSAGES_STORAGE_KEY = 'brightloan_chat_messages'

function loadStoredMessages() {
  try {
    const raw = localStorage.getItem(MESSAGES_STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

// Called from AuthContext's logout so signing out starts a genuinely
// fresh chat next sign-in, instead of resurfacing the previous session's
// conversation from localStorage.
export function clearStoredMessages() {
  try {
    localStorage.removeItem(MESSAGES_STORAGE_KEY)
  } catch {
    // ignore — nothing to clear if storage isn't available
  }
}

// v1 uses a single request/response call per turn. The backend's /chat
// contract (see 01-architecture.md) supports streaming later — swapping
// api.sendMessage for an EventSource/fetch-stream reader here is the only
// change needed when that lands.
export function useChat(userName, phoneNumber) {
  // Initialized from localStorage so a page refresh doesn't wipe the
  // conversation — same pattern as AuthContext's session persistence.
  const [messages, setMessages] = useState(loadStoredMessages)
  const [isLoading, setIsLoading] = useState(false)
  const [loadingStage, setLoadingStage] = useState('')

  useEffect(() => {
    try {
      localStorage.setItem(MESSAGES_STORAGE_KEY, JSON.stringify(messages))
    } catch {
      // localStorage unavailable (e.g. private browsing) — chat just
      // won't survive a refresh; not worth failing the chat over.
    }
  }, [messages])

  // Ref instead of reading `messages` directly in sendMessage — avoids a
  // stale closure without needing `messages` in the callback's deps.
  const messagesRef = useRef([])
  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  const sendMessage = useCallback(async (text) => {
    const userMessage = { type: 'user', text, id: crypto.randomUUID() }
    const history = toHistoryPayload(messagesRef.current)

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)
    setLoadingStage('Understanding your question...')

    const stageTimer = setTimeout(
      () => setLoadingStage('Checking policy documents...'),
      1200,
    )

    try {
      const response = await api.sendMessage(text, userName, phoneNumber, history)
      setMessages((prev) => [...prev, normalizeResponse(response)])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          type: 'agent',
          id: crypto.randomUUID(),
          text: 'Sorry, something went wrong reaching support. Please try again.',
          citations: [],
        },
      ])
      console.error(err)
    } finally {
      clearTimeout(stageTimer)
      setIsLoading(false)
      setLoadingStage('')
    }
  }, [userName, phoneNumber])

  return { messages, isLoading, loadingStage, sendMessage }
}

// Last few turns only, in {role, content} shape the backend expects —
// used by the classifier to rewrite follow-ups into standalone queries
// (see 08 in the PRD / classifier.py). Handoff cards count as "assistant"
// too, since they're still a response the user saw.
function toHistoryPayload(messages) {
  return messages.slice(-HISTORY_MESSAGES).map((m) => ({
    role: m.type === 'user' ? 'user' : 'assistant',
    content: m.text,
  }))
}

// Maps the backend's agent-graph output (see 04 and 05 in the PRD) into
// the shape the message components expect.
function normalizeResponse(response) {
  if (response.type === 'handoff') {
    return {
      type: 'handoff',
      id: crypto.randomUUID(),
      text: response.message,
    }
  }
  return {
    type: 'agent',
    id: crypto.randomUUID(),
    text: response.text || response.message,
    citations: response.citations || [],
  }
}
