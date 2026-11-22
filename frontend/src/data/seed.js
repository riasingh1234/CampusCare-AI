// Demo sign-in shortcuts. The accounts themselves live in Azure SQL (created by `python scripts/init_db.py --demo-users`).
// The password is NOT stored here: it is the one you chose in SEED_DEMO_PASSWORD (or printed once by init_db.py).
export const DEMO_ACCOUNTS = [
  { role: 'student', label: 'Student', email: 'aarav.mehta@campuscare.demo' },
  { role: 'staff', label: 'Maintenance staff', email: 'ravi.sharma@campuscare.demo' },
  { role: 'admin', label: 'Administrator', email: 'meera.kapoor@campuscare.demo' },
];
