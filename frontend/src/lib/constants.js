export const STATUSES = ['Submitted', 'Assigned', 'In Progress', 'Resolved'];
export const PRIORITIES = ['Low', 'Medium', 'High', 'Critical'];
export const PRIORITY_RANK = { Low: 0, Medium: 1, High: 2, Critical: 3 };

// Hours allowed to resolve a complaint, by priority. The Azure timer trigger will reuse these rules.
export const SLA_HOURS = { Critical: 24, High: 48, Medium: 96, Low: 168 };
// A Critical complaint still unresolved after this many hours is flagged for escalation.
export const CRITICAL_FLAG_HOURS = 6;

export const CAMPUS_LOCATIONS = [
  'Academic Block A', 'Academic Block B', 'Computer Lab Block', 'Library', 'Auditorium',
  'Central Cafeteria', 'Boys Hostel 1', 'Girls Hostel 1', 'Sports Complex',
  'Admin Block', 'Main Gate', 'Parking Area',
];

export const ROLES = { student: 'Student', staff: 'Maintenance staff', admin: 'Administrator' };
export const ROLE_HOME = { student: '/student', staff: '/staff', admin: '/admin' };
