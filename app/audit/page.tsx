import AuditLog from '@/components/AuditLog';

export default function AuditPage() {
  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white/90">Agent Audit Log (Article 12)</h1>
          <p className="text-sm text-gray-400 mt-1">Immutable trace of all agent classification and retrieval actions for compliance.</p>
        </div>
        <AuditLog />
      </div>
    </div>
  );
}
