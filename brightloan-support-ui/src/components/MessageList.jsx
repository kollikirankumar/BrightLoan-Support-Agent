import { useEffect, useRef } from 'react'
import UserMessage from './UserMessage.jsx'
import AgentMessage from './AgentMessage.jsx'
import HandoffCard from './HandoffCard.jsx'
import TypingIndicator from './TypingIndicator.jsx'

export default function MessageList({ messages, isLoading, loadingStage }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50/60 px-6 py-4">
      {messages.length === 0 && !isLoading && (
        <p className="mt-10 text-center text-sm text-slate-400">
          Ask about the loan process, offer amounts, or company policy — or
          ask to speak with someone.
        </p>
      )}
      {messages.map((m) => {
        if (m.type === 'user') return <UserMessage key={m.id} text={m.text} />
        if (m.type === 'handoff') return <HandoffCard key={m.id} {...m} />
        return <AgentMessage key={m.id} text={m.text} citations={m.citations} />
      })}
      {isLoading && <TypingIndicator stage={loadingStage} />}
      <div ref={bottomRef} />
    </div>
  )
}
