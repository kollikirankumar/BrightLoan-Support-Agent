// Citation pills are the UI expression of the RAG agent's groundedness
// requirement (see 04-rag-query-agent.md) — a grounded answer always
// carries at least one source; visibly missing pills is a signal
// something upstream returned an ungrounded response.
export default function AgentMessage({ text, citations = [] }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[75%]">
        <div className="whitespace-pre-line rounded-2xl rounded-bl-sm bg-white px-4 py-2 text-sm text-slate-800 shadow-sm ring-1 ring-slate-100">
          {text}
        </div>
        {citations.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {citations.map((citation, i) => (
              <span
                key={i}
                className="rounded-full bg-sky-50 px-2 py-0.5 text-xs font-medium text-sky-600 ring-1 ring-sky-100"
              >
                Source: {citation}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
