'use client';
import { useState } from 'react';
import { CheckCircle2, Circle, ExternalLink } from 'lucide-react';

export interface ComplianceChecklistItem {
  obligation: string;
  article: string;
  description: string;
  deadline: string;
  status: string;
  urgency: string;
}

export default function ComplianceChecklist({ items }: { items: ComplianceChecklistItem[] }) {
  const [completed, setCompleted] = useState<Set<number>>(new Set());

  const toggle = (index: number) => {
    const newSet = new Set(completed);
    if (newSet.has(index)) newSet.delete(index);
    else newSet.add(index);
    setCompleted(newSet);
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'critical': return 'bg-red-500';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  if (!items || items.length === 0) return null;

  return (
    <div className="space-y-3 mt-4 w-full">
      {items.map((item, i) => {
        const isDone = completed.has(i);
        return (
          <div 
            key={i} 
            className={`flex gap-4 p-4 rounded-xl border transition-all cursor-pointer hover:bg-white/[0.04] ${
              isDone ? 'border-emerald-500/30 bg-emerald-500/5 opacity-70' : 'border-white/10 bg-white/[0.02]'
            }`}
            onClick={() => toggle(i)}
          >
            <button className="shrink-0 pt-0.5 text-gray-400 hover:text-white transition-colors">
              {isDone ? <CheckCircle2 className="w-5 h-5 text-emerald-500" /> : <Circle className="w-5 h-5" />}
            </button>
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <h4 className={`text-sm font-semibold transition-colors ${isDone ? 'text-gray-400 line-through' : 'text-white/90'}`}>
                  {item.obligation}
                </h4>
                <a 
                  href={`https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202401689`}
                  target="_blank" rel="noreferrer"
                  onClick={e => e.stopPropagation()}
                  className="flex items-center gap-1 px-2 py-0.5 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-[10px] text-blue-300 transition-colors"
                >
                  <ExternalLink className="w-3 h-3" /> {item.article}
                </a>
              </div>
              <p className={`text-xs mb-3 transition-colors ${isDone ? 'text-gray-500' : 'text-gray-400'}`}>
                {item.description}
              </p>
              <div className="flex items-center gap-3 text-[10px] font-medium tracking-wide">
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-black/30 border border-white/5">
                  <div className={`w-1.5 h-1.5 rounded-full ${getUrgencyColor(item.urgency)}`} />
                  <span className="text-gray-300 capitalize">{item.urgency} Priority</span>
                </div>
                <div className="px-2 py-1 rounded-full bg-black/30 border border-white/5 text-gray-300">
                  Deadline: <span className="text-white">{item.deadline}</span>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
