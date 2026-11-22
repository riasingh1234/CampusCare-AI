import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ClipboardList, Wrench, AlarmClock, CheckCircle2, PartyPopper } from 'lucide-react';
import { useApp } from '../../store/AppContext';
import useLoading from '../../hooks/useLoading';
import { Card, CardHeader } from '../../components/ui/primitives';
import { PageHeader, StatCard, EmptyState, TableSkeleton } from '../../components/ui/feedback';
import ComplaintTable from '../../components/complaints/ComplaintTable';
import { PRIORITY_RANK } from '../../lib/constants';
import { dueAt, isOverdue } from '../../lib/format';

export default function StaffDashboard() {
  const { user, db, maps } = useApp();
  const loading = useLoading();
  const dept = maps.departments.get(user.departmentId)?.name;

  const { open, inProgress, overdue, resolved, queue } = useMemo(() => {
    const mine = db.complaints.filter((c) => c.assignedStaffId === user.id);
    const open = mine.filter((c) => c.status !== 'Resolved');
    return {
      open, resolved: mine.filter((c) => c.status === 'Resolved').length,
      inProgress: open.filter((c) => c.status === 'In Progress').length,
      overdue: open.filter((c) => isOverdue(c)).length,
      queue: [...open].sort((a, b) => PRIORITY_RANK[b.priority] - PRIORITY_RANK[a.priority] || dueAt(a) - dueAt(b)),
    };
  }, [db, user]);

  return (
    <>
      <PageHeader title={`Hello, ${user.name.split(' ')[0]}`} subtitle={`${dept} team. Your queue is ordered by priority, then deadline.`} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Open tasks" value={open.length} icon={ClipboardList} tone="navy" loading={loading} to="/staff/tasks" />
        <StatCard label="In progress" value={inProgress} icon={Wrench} tone="amber" loading={loading} />
        <StatCard label="Overdue" value={overdue} hint={overdue ? 'Past target time' : 'All on time'} icon={AlarmClock} tone={overdue ? 'red' : 'emerald'} loading={loading} />
        <StatCard label="Resolved by you" value={resolved} icon={CheckCircle2} tone="emerald" loading={loading} />
      </div>
      <Card className="mt-6">
        <CardHeader title="Your queue" action={<Link to="/staff/tasks" className="text-[13px] font-bold text-brand-700 hover:underline">All tasks</Link>} />
        {loading ? <TableSkeleton /> : queue.length === 0 ? (
          <EmptyState icon={PartyPopper} title="Queue is clear" description="New assignments from the administrator will appear here." />
        ) : <ComplaintTable complaints={queue} basePath="/staff/tasks" showDue />}
      </Card>
    </>
  );
}
