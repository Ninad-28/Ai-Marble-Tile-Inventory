interface StatCardProps {
  label: string;
  value: string | number;
  icon: string;
  color?: string;
}

export default function StatCard({
  label, value, icon, color = "bg-white"
}: StatCardProps) {
  return (
    <div className={`${color} rounded-xl p-6 shadow-sm border border-stone-200`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-stone-500 text-sm">{label}</p>
          <p className="text-3xl font-bold text-stone-800 mt-1">{value}</p>
        </div>
        <span className="text-4xl">{icon}</span>
      </div>
    </div>
  );
}