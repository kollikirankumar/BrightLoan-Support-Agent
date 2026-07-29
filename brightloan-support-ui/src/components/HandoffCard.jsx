// Deliberately styled as a distinct card, not a chat bubble — this
// represents an action taken on the user's behalf (see 05-human-handoff-agent.md),
// not just generated text. No rep name/slot shown to the customer — this
// is a sales-lead handoff (phone number shared internally), not a booked
// appointment with a named person.
export default function HandoffCard({ text }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 px-4 py-3 shadow-sm">
        <p className="whitespace-pre-line text-sm text-amber-900">{text}</p>
      </div>
    </div>
  )
}
