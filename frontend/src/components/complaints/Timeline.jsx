import { useApp } from '../../store/AppContext';
import { StatusBadge } from '../ui/badges';
import { fmtDateTime } from '../../lib/format';

export default function Timeline({ history }) {
  const { maps } = useApp();
  const items = [...history].sort((a, b) => new Date(b.at) - new Date(a.at));
  return (
    <ul className="space-y-5">
      {items.map((h) => (
        <li key={h.id} className="flex gap-3">
          <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-500" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={h.status} />
              <span className="text-[13px] text-navy-400">{fmtDateTime(h.at)} by {maps.users.get(h.byId)?.name || 'System'}</span>
            </div>
            {h.note && <p className="mt-1.5 text-sm text-navy-700">{h.note}</p>}
          </div>
        </li>
      ))}
    </ul>
  );
}
