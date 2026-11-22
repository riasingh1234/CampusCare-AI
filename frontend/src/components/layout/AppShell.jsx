import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Building2, LayoutDashboard, PlusCircle, ListChecks, ClipboardList, BarChart3, Layers, Inbox, LogOut, Menu, X } from 'lucide-react';
import { useApp } from '../../store/AppContext';
import { ROLES } from '../../lib/constants';
import { initials } from '../../lib/format';
import { cx } from '../ui/primitives';

const NAV = {
  student: [
    { to: '/student', label: 'Overview', icon: LayoutDashboard, end: true },
    { to: '/student/new', label: 'Report an issue', icon: PlusCircle },
    { to: '/student/complaints', label: 'My complaints', icon: ListChecks },
  ],
  staff: [
    { to: '/staff', label: 'Overview', icon: LayoutDashboard, end: true },
    { to: '/staff/tasks', label: 'My tasks', icon: ClipboardList },
  ],
  admin: [
    { to: '/admin', label: 'Overview', icon: LayoutDashboard, end: true },
    { to: '/admin/complaints', label: 'Complaints', icon: Inbox, badge: true },
    { to: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/admin/departments', label: 'Departments', icon: Layers },
  ],
};

function Brand() {
  return (
    <div className="flex items-center gap-2.5 px-3">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-navy-900 text-white"><Building2 className="h-5 w-5" /></span>
      <span className="text-[17px] font-extrabold text-navy-900">CampusCare<span className="ml-1 rounded bg-brand-600 px-1.5 py-0.5 align-middle text-[10px] font-bold text-white">AI</span></span>
    </div>
  );
}

function SidebarBody({ onNavigate }) {
  const { user, db, logout } = useApp();
  const unassigned = db.complaints.filter((c) => c.status === 'Submitted').length;
  return (
    <div className="flex h-full flex-col">
      <div className="py-5"><Brand /></div>
      <nav className="flex-1 space-y-1 px-3" aria-label="Main">
        {NAV[user.role].map(({ to, label, icon: Icon, end, badge }) => (
          <NavLink
            key={to} to={to} end={end} onClick={onNavigate}
            className={({ isActive }) => cx('flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition-colors',
              isActive ? 'bg-brand-50 text-brand-700' : 'text-navy-500 hover:bg-navy-50 hover:text-navy-800')}
          >
            <Icon className="h-[18px] w-[18px]" />
            <span className="flex-1">{label}</span>
            {badge && unassigned > 0 && <span className="rounded-full bg-brand-600 px-2 py-0.5 text-[11px] font-bold text-white">{unassigned}</span>}
          </NavLink>
        ))}
      </nav>
      <div className="m-3 flex items-center gap-3 rounded-xl bg-navy-50 p-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-navy-900 text-xs font-bold text-white">{initials(user.name)}</span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] font-bold text-navy-900">{user.name}</p>
          <p className="truncate text-xs text-navy-500">{ROLES[user.role]}</p>
        </div>
        <button onClick={logout} aria-label="Sign out" className="rounded-md p-1.5 text-navy-400 hover:bg-navy-100 hover:text-navy-800"><LogOut className="h-4 w-4" /></button>
      </div>
    </div>
  );
}

export default function AppShell() {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-navy-100 bg-white lg:block"><SidebarBody /></aside>

      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-navy-100 bg-white px-4 lg:hidden">
        <Brand />
        <button onClick={() => setOpen(true)} aria-label="Open menu" className="rounded-md p-2 text-navy-600 hover:bg-navy-100"><Menu className="h-5 w-5" /></button>
      </header>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-navy-900/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 bg-white shadow-pop">
            <button onClick={() => setOpen(false)} aria-label="Close menu" className="absolute right-3 top-4 rounded-md p-1.5 text-navy-400 hover:bg-navy-100"><X className="h-5 w-5" /></button>
            <SidebarBody onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}

      <main className="lg:pl-64">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-8 sm:py-9"><Outlet /></div>
      </main>
    </div>
  );
}
