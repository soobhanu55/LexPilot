'use client';
import { useState, useEffect } from 'react';
import { Activity, Clock } from 'lucide-react';

export default function AuditLog() {
  const [logs, setLogs] = useState<any[]>([]);
  const companyId = 'demo-company';

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || '/api'}/audit/${companyId}`)
      .then(r => r.json())
      .then(data => setLogs(data || []))
      .catch(console.error);
  }, []);

  return (
    <div className="space-y-4">
      {logs.map((log, i) => (
        <div key={i} className="flex gap-4 p-5 border border-white/10 bg-white/[0.02] rounded-xl hover:bg-white/[0.04] transition-colors relative group">
          <div className="shrink-0 w-10 h-10 flex items-center justify-center rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Activity className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-semibold text-white/90">Agent: {log.agent_name}</h3>
              <span className="text-xs text-gray-500 flex items-center gap-1"><Clock className="w-3 h-3"/> {new Date(log.created_at).toLocaleString()}</span>
            </div>
            <p className="text-xs text-gray-400 uppercase tracking-widest font-semibold mb-3">ACTION: {log.action}</p>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-black/30 p-3 rounded-md border border-white/5 font-mono text-[10px] text-gray-400 overflow-x-auto">
                <span className="text-blue-400 mb-1 block">Input Payload</span>
                {JSON.stringify(log.input, null, 2)}
              </div>
              <div className="bg-black/30 p-3 rounded-md border border-white/5 font-mono text-[10px] text-gray-400 overflow-x-auto">
                <span className="text-emerald-400 mb-1 block">Output Payload</span>
                {JSON.stringify(log.output, null, 2)}
              </div>
            </div>
          </div>
          <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-[10px] px-2 py-1 bg-white/10 rounded-full text-gray-300">{log.latency_ms} ms</span>
          </div>
        </div>
      ))}
    </div>
  );
}
