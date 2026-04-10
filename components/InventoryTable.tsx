'use client';
import { useState, useEffect } from 'react';
import { Trash2, AlertCircle } from 'lucide-react';
import ComplianceChecklist from './ComplianceChecklist';

export default function InventoryTable() {
  const [systems, setSystems] = useState<any[]>([]);
  const companyId = 'demo-company';

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || '/backend-api'}/inventory/${companyId}`)
      .then(r => r.json())
      .then(data => setSystems(data || []))
      .catch(console.error);
  }, []);

  const getTierColor = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'prohibited': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'high-risk': return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
      case 'limited-risk': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      case 'minimal-risk': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      default: return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
    }
  };

  return (
    <div className="w-full border border-white/10 rounded-xl bg-black/20 overflow-hidden shadow-2xl backdrop-blur-md">
      <table className="w-full text-left text-sm">
        <thead className="bg-white/5 border-b border-white/10">
          <tr>
            <th className="px-6 py-4 font-medium text-gray-300">System Name</th>
            <th className="px-6 py-4 font-medium text-gray-300 w-1/3">Description</th>
            <th className="px-6 py-4 font-medium text-gray-300">Risk Tier</th>
            <th className="px-6 py-4 font-medium text-gray-300">Status</th>
            <th className="px-6 py-4 font-medium text-gray-300">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {systems.map((s, i) => (
            <tr key={i} className="hover:bg-white/[0.02] transition-colors">
              <td className="px-6 py-4 font-medium">{s.system_name}</td>
              <td className="px-6 py-4 text-gray-400 text-xs">{s.description}</td>
              <td className="px-6 py-4">
                <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${getTierColor(s.risk_tier)}`}>
                  {s.risk_tier}
                </span>
              </td>
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${s.compliance_status === 'compliant' ? 'bg-emerald-500' : 'bg-yellow-500'}`} />
                  <span className="capitalize text-gray-300">{s.compliance_status}</span>
                </div>
              </td>
              <td className="px-6 py-4">
                <button className="p-2 text-gray-400 hover:text-white rounded-md hover:bg-white/10 transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </td>
            </tr>
          ))}
          {systems.length === 0 && (
            <tr>
              <td colSpan={5} className="px-6 py-12 text-center text-gray-500 italic">
                No AI systems found. Use the Chat agent to add one.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
