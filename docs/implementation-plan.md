# Implementation status

"Locally verified" = automated tests on your computer, no Azure. "Needs Azure" = written but never run against the real service. See `testing.md`.

| # | Feature | Service | Status |
|---|---|---|---|
| 1 | Complaint submission | Functions + SQL | Done. Locally verified; SQL needs Azure |
| 2 | AI classification | Foundry | Done. Fallback locally verified; Foundry call needs Azure |
| 3 | Rule-based fallback | Python | Done. Locally verified |
| 4 | Image / PDF upload | Blob Storage | Done. Checks locally verified; upload needs Azure |
| 5 | Assignment | Functions + SQL | Done. Locally verified; SQL needs Azure |
| 6 | Tracking and status history | SQL + React | Done. Locally verified; SQL needs Azure |
| 7 | Escalation: timer every 6 h + admin button, no duplicates | Timer + SQL | Done. Logic locally verified; timer needs Azure |
| 8 | Analytics from SQL with Recharts | SQL + React | Done. Numbers locally verified; SQL needs Azure |
| 9 | Speech to text on the complaint form | Azure AI Speech | Done. Logic locally verified; live speech needs Azure |
| 10 | Duplicate warning | Python + SQL | Done. Locally verified |

Stages 1-9 are complete in code. What remains is yours: create the Azure resources and follow `azure-checklist.md`.
