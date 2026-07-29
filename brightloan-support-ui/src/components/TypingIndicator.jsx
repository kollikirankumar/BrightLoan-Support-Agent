// Staged text ("Understanding your question..." -> "Checking policy
// documents...") instead of a generic spinner, since a real request
// takes a few seconds while the agent graph runs classifier -> agent ->
// supervisor sequentially (see 01-architecture.md).
export default function TypingIndicator({ stage }) {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-white px-4 py-2 text-xs text-slate-500 shadow-sm ring-1 ring-slate-100">
        <span className="flex gap-1">
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 [animation-delay:-0.3s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 [animation-delay:-0.15s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400" />
        </span>
        {stage || 'Thinking...'}
      </div>
    </div>
  )
}
