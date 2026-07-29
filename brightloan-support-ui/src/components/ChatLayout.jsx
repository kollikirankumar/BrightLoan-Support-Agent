import Header from './Header.jsx'
import MessageList from './MessageList.jsx'
import ChatInput from './ChatInput.jsx'
import { useChat } from '../hooks/useChat.js'
import { useAuth } from '../context/AuthContext.jsx'

export default function ChatLayout() {
  const { user } = useAuth()
  const { messages, isLoading, loadingStage, sendMessage } = useChat(user?.name, user?.phone)

  return (
    <div className="flex h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-3xl bg-white shadow-xl shadow-indigo-100 ring-1 ring-slate-100">
      <Header />
      <MessageList messages={messages} isLoading={isLoading} loadingStage={loadingStage} />
      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  )
}
