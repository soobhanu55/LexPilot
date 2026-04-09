import { FileText } from "lucide-react";

export default function MessageBubble({ role, content, citations }: { role: 'user'|'agent', content: string, citations?: string[] }) {
  const isAgent = role === 'agent';
  
  return (
    <div className={`flex w-full ${isAgent ? 'justify-start' : 'justify-end'}`}>
      <div className={`max-w-[80%] rounded-2xl p-5 ${
        isAgent 
          ? 'bg-white/5 border border-white/10 text-gray-200 shadow-sm backdrop-blur-sm' 
          : 'bg-blue-600/90 text-white shadow-md'
      }`}>
        <div className="prose prose-invert max-w-none text-sm whitespace-pre-wrap leading-relaxed">
          {content}
        </div>
        
        {citations && citations.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2 pt-3 border-t border-white/10">
            {citations.map((cite, i) => (
              <a 
                key={i}
                href={`https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202401689`}
                target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-white/20 bg-black/30 hover:bg-white/10 text-xs text-blue-300 hover:text-blue-200 transition-colors cursor-pointer"
                title="View in EUR-Lex"
              >
                <FileText className="w-3 h-3" />
                {cite}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
