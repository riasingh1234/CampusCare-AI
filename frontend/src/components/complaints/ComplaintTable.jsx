import { useNavigate } from 'react-router-dom';
import { useApp } from '../../store/AppContext';
import { StatusBadge, PriorityBadge, Tag } from '../ui/badges';
import { fmtDate, isOverdue, dueAt, overdueBy } from '../../lib/format';

export default function ComplaintTable({ complaints, basePath, showStudent, showAssignee, showDue }) {
  const { maps } = useApp();
  const navigate = useNavigate();
  const now = Date.now();
  const go = (c) => navigate(`${basePath}/${c.id}`);

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-left text-sm">
        <thead>
          <tr className="border-b border-navy-100 text-xs font-semibold text-navy-400">
            <th className="px-5 py-3 font-semibold">Complaint</th>
            <th className="px-3 py-3 font-semibold">Category</th>
            <th className="px-3 py-3 font-semibold">Priority</th>
            <th className="px-3 py-3 font-semibold">Status</th>
            {showStudent && <th className="px-3 py-3 font-semibold">Reported by</th>}
            {showAssignee && <th className="px-3 py-3 font-semibold">Assigned to</th>}
            <th className="px-5 py-3 font-semibold">{showDue ? 'Due' : 'Reported'}</th>
          </tr>
        </thead>
        <tbody>
          {complaints.map((c) => {
            const overdue = isOverdue(c, now);
            return (
              <tr
                key={c.id}
                tabIndex={0}
                onClick={() => go(c)}
                onKeyDown={(e) => e.key === 'Enter' && go(c)}
                className="cursor-pointer border-b border-navy-50 last:border-0 hover:bg-navy-50/70 focus-visible:bg-navy-50"
              >
                <td className="max-w-[300px] px-5 py-3.5">
                  <p className="text-xs font-bold text-brand-700">{c.id}</p>
                  <p className="truncate font-semibold text-navy-900">{c.title}</p>
                  <p className="truncate text-[13px] text-navy-400">{c.location}</p>
                </td>
                <td className="px-3 py-3.5 text-navy-600">{maps.categories.get(c.categoryId)?.name}</td>
                <td className="px-3 py-3.5"><PriorityBadge priority={c.priority} /></td>
                <td className="px-3 py-3.5">
                  <div className="flex flex-col items-start gap-1">
                    <StatusBadge status={c.status} />
                    {overdue && <Tag tone="red">Overdue {overdueBy(c, now)}</Tag>}
                  </div>
                </td>
                {showStudent && <td className="px-3 py-3.5 text-navy-600">{maps.users.get(c.studentId)?.name}</td>}
                {showAssignee && (
                  <td className="px-3 py-3.5 text-navy-600">
                    {c.assignedStaffId ? maps.users.get(c.assignedStaffId)?.name : <span className="text-navy-300">Not assigned</span>}
                  </td>
                )}
                <td className="whitespace-nowrap px-5 py-3.5 text-navy-500">{fmtDate(showDue ? dueAt(c) : c.createdAt)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
