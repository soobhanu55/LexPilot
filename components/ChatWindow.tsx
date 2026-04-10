'use client';
import { useState, useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import { Send, Loader2 } from 'lucide-react';

export default function ChatWindow() {
  const [messages, setMessages] = useState<{role: 'user'|'agent', content: string, citations?: string[]}[]>([]);
  const [input, setInput] = useState('');
  const [companyId, setCompanyId] = useState('demo-company');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    
    const userMessage = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || '/backend-api';
      console.log("Current API Base URL:", baseUrl);
      const resp = await fetch(`${baseUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, company_id: companyId, session_id: 'session-' + Date.now() })
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(`API Error (${resp.status}): ${errorText}`);
      }

      if (!resp.body) throw new Error("No body");
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      
      let agentMessage = '';
      let currentCitations: string[] = [];

      setMessages(prev => [...prev, { role: 'agent', content: '' }]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'answer' && data.text) {
                agentMessage += data.text;
                setMessages(prev => {
                  const newArr = [...prev];
                  newArr[newArr.length - 1] = { role: 'agent', content: agentMessage, citations: currentCitations };
                  return newArr;
                });
              } else if (data.type === 'citations') {
                currentCitations = data.articles;
              } else if (data.type === 'status') {
                console.log("Agent status:", data.message);
              }
            } catch (e) {
              // Parse error on incomplete chunks
            }
          }
        }
      }
    } catch (error) {
      console.error(error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown connection error';
      setMessages(prev => [...prev, { role: 'agent', content: `Sorry, I encountered an error: ${errorMessage}. Please check your API configuration and Vercel environment variables.` }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full relative">
      <div className="px-6 py-2 border-b border-white/5 flex gap-4 items-center bg-black/20 justify-between">
        <div className="flex gap-4 items-center">
          <span className="text-xs text-gray-500 font-medium">COMPANY ID</span>
          <input 
            type="text" 
            value={companyId} 
            onChange={e => setCompanyId(e.target.value)}
            className="bg-transparent border border-white/10 rounded px-2 py-1 text-sm text-gray-300 focus:outline-none focus:border-blue-500 w-48 transition-colors"
          />
        </div>
        <span className="text-[10px] text-gray-600 font-mono">v1.0.2-diag</span>
      </div>
      
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-gray-500 space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center p-4">
              <svg className="w-full h-full text-blue-500/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <p>Describe your AI system for an instant risk assessment.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} content={m.content} citations={m.citations} />
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-gray-500 text-sm pl-4">
            <Loader2 className="w-4 h-4 animate-spin" /> LexAgent is thinking...
          </div>
        )}
      </div>

      <div className="p-4 bg-gradient-to-t from-black/20 to-transparent">
        <div className="max-w-4xl mx-auto relative rounded-xl border border-white/10 bg-white/5 backdrop-blur-md overflow-hidden focus-within:ring-1 focus-within:ring-blue-500/50 transition-all">
          <textarea 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="e.g., We are building a CV screening tool using LLMs..."
            className="w-full bg-transparent p-4 pr-12 outline-none resize-none text-sm min-h-[50px] max-h-[200px]"
            rows={1}
          />
          <button 
            onClick={sendMessage}
            className="absolute right-2 bottom-2 p-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50"
            disabled={!input.trim() || isLoading}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
