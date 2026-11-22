import { useMemo, useState } from 'react';
import { ClipboardCheck } from 'lucide-react';
import { useApp } from '../../store/AppContext';
import useLoading from '../../hooks/useLoading';
import { Card, cx } from '../../components/ui/primitives';
import { PageHeader, EmptyState, TableSkeleton } from '../../components/ui/feedback';
import ComplaintTable from '../../components/complaints/ComplaintTable';
import { PRIORITY_RANK } from '../../lib/constants';
import { dueAt } from '../../lib/format';

const TABS = ['Open', 'Resolved', 'All'];

export default function StaffTasks() {
  const { user, db } = useApp();
  const loading = useLoading();
  const [tab, setTab] = useState('Open');
  const mine = useMemo(() => db.complaints.filter((c) => c.assignedStaffId === user.id), [db, user]);
  const list = useMemo(() => mine
    .filter((c) => tab === 'All' || (tab === 'Open' ? c.status !== 'Resolved' : c.status === 'Resolved'))
    .sort((a, b) => (tab === 'Resolved' ? new Date(b.resolvedAt) - new Date(a.resolvedAt) : PRIORITY_RANK[b.priority] - PRIORITY_RANK[a.priority] || dueAt(a) - dueAt(b))), [mine, tab]);

  return (
    <>
      <PageHeader title="My tasks" subtitle="Open a task to see photos, update its status and add notes." />
      <Card>
        <div className="flex gap-1.5 border-b border-navy-100 p-4">
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)} aria-pressed={tab === t}
              className={cx('rounded-full px-3.5 py-1.5 text-[13px] font-semibold transition-colors', tab === t ? 'bg-navy-900 text-white' : 'bg-navy-50 text-navy-600 hover:bg-navy-100')}>
              {t}
            </button>
          ))}
        </div>
        {loading ? <TableSkeleton /> : list.length === 0 ? (
          <EmptyState icon={ClipboardCheck} title={`No ${tab.toLowerCase()} tasks`} description="Tasks assigned to you will show up here." />
        ) : <ComplaintTable complaints={list} basePath="/staff/tasks" showDue={tab !== 'Resolved'} />}
      </Card>
    </>
  );
}
