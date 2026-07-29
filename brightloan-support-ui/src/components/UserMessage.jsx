export default function UserMessage({ text }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-gradient-to-br from-indigo-600 to-blue-600 px-4 py-2 text-sm text-white shadow-sm">
        {text}
      </div>
    </div>
  )
}
