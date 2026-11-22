# Database schema (Azure SQL)

The real scripts are `database/schema.sql` (tables, constraints, indexes) and `database/seed.sql` (departments and categories).

**The six core tables** from the project brief: `Users`, `Departments`, `Complaints`, `Assignments`, `StatusHistory`, `Feedback`.

**Four supporting tables** that the final feature list needs, so they were added:

| Table | Why it is needed |
|---|---|
| `Categories` | Admins manage categories, and their keywords drive the rule-based classifier (already in the frontend) |
| `Attachments` | Image/document uploads tied to a complaint; stores only the blob name |
| `Escalations` | The record the timer creates; one per complaint per reason so nothing escalates twice |
| `Notifications` | Reserved for in-app alerts. **Not used yet**: escalations appear as an "Escalated" tag and a timeline entry instead |

Key design points:
- `Complaints.Reference` (CC-2026-0001) is the public ID; `ComplaintId` is the internal key.
- `Assignments` keeps history; a unique filtered index allows exactly one `IsCurrent = 1` row per complaint.
- `StatusHistory.ChangedBy` is NULL when the system made the change (timer escalation).
- `Complaints.DueAt` is stored at creation from the SLA hours (Critical 24, High 48, Medium 96, Low 168) so the timer can find overdue rows with one indexed query.
- Passwords are stored only as Argon2 hashes. The seed script contains no users or passwords.
