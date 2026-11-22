import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Inbox, Search } from 'lucide-react';
import { useApp } from '../../store/AppContext';
import useLoading from '../../hooks/useLoading';
import { Card, Input, Select } from '../../components/ui/primitives';
import { PageHeader, EmptyState, TableSkeleton } from '../../components/ui/feedback';
import ComplaintTable from '../../components/complaints/ComplaintTable';
import { PRIORITIES, STATUSES } from '../../lib/constants';
import { isCriticalFlagged, isOverdue } from '../../lib/format';

const QUICK = { '': 'All complaints', overdue: 'Overdue', unassigned: 'Awaiting assignment', critical: 'Critical, unresolved' };

export default function AdminComplaints() {
  const { db } = useApp();
  const loading = useLoading();
  const [params, setParams] = useSearchParams();
  const quick = params.get('filter') || '';
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [priority, setPriority] = useState('');
  const [dept, setDept] = useState('');

  const list = useMemo(() => db.complaints.filter((c) => {
    if (quick === 'overdue' && !isOverdue(c)) return false;
    if (quick === 'unassigned' && !(c.status !== 'Resolved' && !c.assignedStaffId)) return false;
    if (quick === 'critical' && !isCriticalFlagged(c)) return false;
    if (status && c.status !== status) return false;
    if (priority && c.priority !== priority) return false;
    if (dept && c.departmentId !== dept) return false;
    return `${c.id} ${c.title} ${c.location}`.toLowerCase().includes(q.trim().toLowerCase());
  }), [db.complaints, quick, status, priority, dept, q]);

  return (
    <>
      <PageHeader title="Complaints" subtitle={`${list.length} shown. Open a complaint to assign it or review its history.`} />
      <Card>
        <div className="grid gap-3 border-b border-navy-100 p-4 sm:grid-cols-2 lg:grid-cols-5">
          <div className="relative lg:col-span-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-navy-300" />
            <Input aria-label="Search complaints" placeholder="Search" className="pl-9" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Select aria-label="Quick filter" value={quick} onChange={(e) => setParams(e.target.value ? { filter: e.target.value } : {})}>
            {Object.entries(QUICK).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
          <Select aria-label="Status" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Any status</option>{STATUSES.map((s) => <option key={s}>{s}</option>)}</Select>
          <Select aria-label="Priority" value={priority} onChange={(e) => setPriority(e.target.value)}><option value="">Any priority</option>{PRIORITIES.map((p) => <option key={p}>{p}</option>)}</Select>
          <Select aria-label="Department" value={dept} onChange={(e) => setDept(e.target.value)}><option value="">Any department</option>{db.departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</Select>
        </div>
        {loading ? <TableSkeleton /> : list.length === 0 ? (
          <EmptyState icon={Inbox} title="No complaints match these filters" description="Clear a filter or search for a different word." />
        ) : <ComplaintTable complaints={list} basePath="/admin/complaints" showStudent showAssignee />}
      </Card>
    </>
  );
}
