import { CalendarAlert } from "lucide-react";

export default function DeadlineCard({ system, deadline, days_remaining, urgency }: any) {
  const getColors = () => {
    switch(urgency) {
      case 'critical': return "bg-red-500/10 border-red-500/30 text-red-400";
      case 'high': return "bg-orange-500/10 border-orange-500/30 text-orange-400";
      case 'medium': return "bg-yellow-500/10 border-yellow-500/30 text-yellow-400";
      case 'low': return "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
      default: return "bg-gray-500/10 border-gray-500/30 text-gray-400";
    }
  };

  return (
    <div className={`p-4 rounded-xl border flex items-center gap-4 ${getColors()} backdrop-blur-md`}>
      <div className="p-2 bg-black/20 rounded-lg">
        <CalendarAlert className="w-5 h-5" />
      </div>
      <div>
        <h4 className="text-sm font-semibold">{system}</h4>
        <p className="text-xs opacity-80">{deadline} • {days_remaining > 0 ? `${days_remaining} days left` : 'Overdue'}</p>
      </div>
    </div>
  );
}
