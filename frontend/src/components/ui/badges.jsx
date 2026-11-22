const STATUS = {
  Submitted: ['bg-navy-100 text-navy-700', 'bg-navy-400'],
  Assigned: ['bg-brand-50 text-brand-700', 'bg-brand-500'],
  'In Progress': ['bg-amber-50 text-amber-700', 'bg-amber-500'],
  Resolved: ['bg-emerald-50 text-emerald-700', 'bg-emerald-500'],
};
const PRIORITY = {
  Low: ['bg-navy-50 text-navy-600', 'bg-navy-300'],
  Medium: ['bg-sky-50 text-sky-700', 'bg-sky-500'],
  High: ['bg-orange-50 text-orange-700', 'bg-orange-500'],
  Critical: ['bg-red-50 text-red-700', 'bg-red-600'],
};

function Pill({ cls, dot, children }) {
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />{children}
    </span>
  );
}

export const StatusBadge = ({ status }) => <Pill cls={STATUS[status][0]} dot={STATUS[status][1]}>{status}</Pill>;
export const PriorityBadge = ({ priority }) => <Pill cls={PRIORITY[priority][0]} dot={PRIORITY[priority][1]}>{priority}</Pill>;
export const Tag = ({ tone = 'navy', children }) => {
  const t = { navy: 'bg-navy-100 text-navy-700', red: 'bg-red-50 text-red-700', amber: 'bg-amber-50 text-amber-700', brand: 'bg-brand-50 text-brand-700' }[tone];
  return <span className={`inline-flex whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-semibold ${t}`}>{children}</span>;
};
