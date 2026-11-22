import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Inbox, PlusCircle, Search } from 'lucide-react';
import { useApp } from '../../store/AppContext';
import useLoading from '../../hooks/useLoading';
import { Button, Card, Input, cx } from '../../components/ui/primitives';
import { PageHeader, EmptyState, TableSkeleton } from '../../components/ui/feedback';
import ComplaintTable from '../../components/complaints/ComplaintTable';
import { STATUSES } from '../../lib/constants';

export default function MyComplaints() {
  const { user, db } = useApp();
  const loading = useLoading();
  const [status, setStatus] = useState('All');
  const [q, setQ] = useState('');

  const mine = useMemo(() => db.complaints.filter((c) => c.studentId === user.id), [db, user]);
  const list = useMemo(() => mine.filter((c) =>
    (status === 'All' || c.status === status) &&
    `${c.id} ${c.title} ${c.location}`.toLowerCase().includes(q.trim().toLowerCase())), [mine, status, q]);

  return (
    <>
      <PageHeader title="My complaints" subtitle="Your full history. Open any complaint to see its progress." actions={<Link to="/student/new"><Button icon={PlusCircle}>Report an issue</Button></Link>} />
      <Card>
        <div className="flex flex-wrap items-center gap-3 border-b border-navy-100 p-4">
          <div className="flex flex-wrap gap-1.5">
            {['All', ...STATUSES].map((s) => (
              <button key={s} onClick={() => setStatus(s)} aria-pressed={status === s}
                className={cx('rounded-full px-3.5 py-1.5 text-[13px] font-semibold transition-colors', status === s ? 'bg-navy-900 text-white' : 'bg-navy-50 text-navy-600 hover:bg-navy-100')}>
                {s}
              </button>
            ))}
          </div>
          <div className="relative ml-auto w-full sm:w-64">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-navy-300" />
            <Input aria-label="Search complaints" placeholder="Search by ID, title or place" className="pl-9" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
        </div>
        {loading ? <TableSkeleton /> : list.length === 0 ? (
          <EmptyState icon={Inbox} title={mine.length ? 'No complaints match' : 'No complaints yet'}
            description={mine.length ? 'Try another status or clear the search.' : 'Report your first issue to start tracking it here.'}
            action={!mine.length && <Link to="/student/new"><Button icon={PlusCircle}>Report an issue</Button></Link>} />
        ) : <ComplaintTable complaints={list} basePath="/student/complaints" />}
      </Card>
    </>
  );
}
