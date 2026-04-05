import ChatWindow from '@/components/ChatWindow';

export default function ChatPage() {
  return (
    <div className="flex-1 flex flex-col h-full bg-gradient-to-b from-transparent to-black/5">
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
        <h1 className="text-lg font-medium">Compliance Assistant</h1>
      </div>
      <ChatWindow />
    </div>
  );
}
