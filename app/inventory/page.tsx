import InventoryTable from '@/components/InventoryTable';

export default function InventoryPage() {
  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white/90">AI Inventory Dashboard</h1>
          <p className="text-sm text-gray-400 mt-1">Manage and track your AI systems for EU AI Act compliance.</p>
        </div>
        <InventoryTable />
      </div>
    </div>
  );
}
