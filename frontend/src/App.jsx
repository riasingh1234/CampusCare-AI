import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useApp } from './store/AppContext';
import { ROLE_HOME } from './lib/constants';
import AppShell from './components/layout/AppShell';
import Login from './pages/Login';
import Register from './pages/Register';
import StudentDashboard from './pages/student/StudentDashboard';
import NewComplaint from './pages/student/NewComplaint';
import MyComplaints from './pages/student/MyComplaints';
import StaffDashboard from './pages/staff/StaffDashboard';
import StaffTasks from './pages/staff/StaffTasks';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminComplaints from './pages/admin/AdminComplaints';
import AdminAnalytics from './pages/admin/AdminAnalytics';
import AdminDepartments from './pages/admin/AdminDepartments';
import ComplaintDetail from './pages/ComplaintDetail';

function RequireRole({ role, children }) {
  const { user } = useApp();
  const location = useLocation();
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (user.role !== role) return <Navigate to={ROLE_HOME[user.role]} replace />;
  return children;
}

function PublicOnly({ children }) {
  const { user } = useApp();
  return user ? <Navigate to={ROLE_HOME[user.role]} replace /> : children;
}

function Home() {
  const { user } = useApp();
  return <Navigate to={user ? ROLE_HOME[user.role] : '/login'} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />

      <Route path="/student" element={<RequireRole role="student"><AppShell /></RequireRole>}>
        <Route index element={<StudentDashboard />} />
        <Route path="new" element={<NewComplaint />} />
        <Route path="complaints" element={<MyComplaints />} />
        <Route path="complaints/:id" element={<ComplaintDetail role="student" />} />
      </Route>

      <Route path="/staff" element={<RequireRole role="staff"><AppShell /></RequireRole>}>
        <Route index element={<StaffDashboard />} />
        <Route path="tasks" element={<StaffTasks />} />
        <Route path="tasks/:id" element={<ComplaintDetail role="staff" />} />
      </Route>

      <Route path="/admin" element={<RequireRole role="admin"><AppShell /></RequireRole>}>
        <Route index element={<AdminDashboard />} />
        <Route path="complaints" element={<AdminComplaints />} />
        <Route path="complaints/:id" element={<ComplaintDetail role="admin" />} />
        <Route path="analytics" element={<AdminAnalytics />} />
        <Route path="departments" element={<AdminDepartments />} />
      </Route>

      <Route path="*" element={<Home />} />
    </Routes>
  );
}
