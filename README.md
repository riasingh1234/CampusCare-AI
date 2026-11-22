# CampusCare AI

AI-powered campus issue reporting and maintenance management. Students report problems (by typing or speaking), the system
suggests a category, priority and department, administrators assign staff, staff update progress, and overdue or critical
complaints are escalated automatically.

**Azure services used (only these five):** Azure Functions (Python 3.12, HTTP APIs + timer) · Azure SQL Database ·
Azure Blob Storage · Azure AI Foundry · Azure AI Speech.

## The 10 features

| # | Feature | Where it lives |
|---|---|---|
| 1 | Complaint submission (description, location) | `api/complaints.py`, `pages/student/NewComplaint.jsx` |
| 2 | AI classification (category, priority, department) | `services/classifier.py` → Azure AI Foundry |
| 3 | Rule-based fallback (works with AI off or down) | `services/classifier.py` (`classify_rules`) |
| 4 | Image / PDF upload | `services/blob_storage.py` → Azure Blob Storage |
| 5 | Assignment to staff by an admin | `POST /complaints/{id}/assign` |
| 6 | Tracking, staff updates, status history | `POST /complaints/{id}/status`, `StatusHistory` table |
| 7 | Automatic escalation every 6 hours + admin button | `timers/escalation.py`, `services/escalation.py` |
| 8 | Admin analytics from real SQL data (Recharts) | `services/analytics.py`, `pages/admin/AdminAnalytics.jsx` |
| 9 | Speech to text (microphone button on the complaint form) | `services/speech.py` (token), `lib/speech.js` (Azure Speech SDK) |
| 10 | Duplicate complaint warning | `services/duplicates.py` |

## Structure

```
campuscare-ai/
  frontend/   React + Vite + Tailwind + Recharts. One API helper: src/lib/api.js
  backend/    Azure Functions (Python v2): api/ services/ repositories/ timers/ core/ scripts/ tests/
  database/   schema.sql, seed.sql, grant_access.sql
  docs/       azure-checklist.md (start here), architecture.md, testing.md, azure-setup.md
```

## Quick start (after your Azure resources exist, see `docs/azure-checklist.md`)

Terminal 1, backend (one-time setup first):
```bash
cd backend
python -m venv .venv
source .venv/bin/activate                  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp local.settings.example.json local.settings.json   # Windows: copy ...   then fill in the values
az login
python scripts/check_config.py             # tells you what is still missing
export SEED_DEMO_PASSWORD='Demo@1234'      # Windows PowerShell: $env:SEED_DEMO_PASSWORD='Demo@1234'
python scripts/init_db.py --demo-users     # creates tables, departments, categories, demo accounts
python scripts/seed_demo_complaints.py     # optional: sample complaints so the charts have data
npx azurite --silent --location .azurite   # (separate terminal) local storage the timer trigger needs
func start                                  # API at http://localhost:7071/api
```
Terminal 2, frontend:
```bash
cd frontend
npm install
cp .env.example .env                       # Windows: copy .env.example .env
npm run dev                                # http://localhost:5173
```

Demo accounts (password = the `SEED_DEMO_PASSWORD` you chose): `aarav.mehta@campuscare.demo` (student),
`ravi.sharma@campuscare.demo` (electrical staff), `meera.kapoor@campuscare.demo` (admin). The sign-in page has buttons that fill the email.

## Run the tests (no Azure needed)

```bash
cd backend  && python -m unittest discover -s tests -t .      # 144 tests
cd frontend && npm test                                       # 25 tests (API helper, data mapping, speech logic)
```
`docs/testing.md` lists exactly what is verified locally and what can only be verified with real Azure resources.

## Security rules

No secrets in React or git. The browser only knows the public API address. `local.settings.json` and `.env` are git-ignored.
SQL is parameterized, every input is validated on the server, roles come from the signed token, uploaded files are checked by
their real content and stored in a private container, and the Speech key never leaves the backend (the browser gets a 10-minute token).
