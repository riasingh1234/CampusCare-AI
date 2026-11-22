# CampusCare AI: architecture (for evaluation)

## One-minute explanation

A React website talks to a small Python API running on **Azure Functions**. The API stores everything in **Azure SQL**, keeps uploaded
photos in **Blob Storage**, asks **Azure AI Foundry** to classify complaints, and hands the browser a temporary token so it can use
**Azure AI Speech** for voice input. A **timer** in the same Function App escalates overdue complaints every 6 hours.

```
 Browser (React, runs locally)
   |  HTTPS + JWT                         microphone audio (direct, short-lived token)
   v                                                   |
 Azure Functions (Python 3.12) ----------------------> Azure AI Speech
   |-- HTTP APIs (api/)                                 (speech to text)
   |-- Timer trigger every 6 h (timers/)
   |-- Azure SQL Database  <- all application data (managed identity, no password)
   |-- Blob Storage        <- photos / PDFs (private container, managed identity)
   '-- Azure AI Foundry    <- classification (rules take over if it fails)
```

## Layers (each file has one job)

| Layer | Folder | Job |
|---|---|---|
| Endpoint | `backend/api/` | Check who is calling, read input, call a service, return JSON |
| Service | `backend/services/` | The rules: classify, find duplicates, escalate, count analytics, who may do what |
| Repository | `backend/repositories/` | The only place with SQL (always parameterized) |
| Core | `backend/core/` | Settings, Azure clients, passwords/tokens, validation, errors |
| Frontend | `frontend/src/` | Screens. `lib/api.js` is the single place that calls the backend |

## Request flow: submitting a complaint

1. Student types or speaks (speech goes browser → Azure Speech, text lands in the same box and stays editable).
2. After a pause the page calls `POST /ai/classify` and `POST /complaints/duplicates` to show suggestions and a duplicate warning.
3. **Submit** → `POST /complaints`: the server validates, classifies again (it never trusts the browser), computes the deadline from the priority, saves the complaint and its first history entry.
4. Each chosen file → `POST /complaints/{id}/attachments`: the server checks size and real file type, writes to Blob Storage, then saves only the blob name in SQL.
5. Admin assigns → staff updates → every change adds a `StatusHistory` row the student can see.

## Classification (features 2 and 3)

`classify()` tries Foundry only if `AI_ENABLED=true`. Foundry must answer with JSON naming a category from our list and a valid priority, otherwise
the answer is thrown away. Any error or timeout (15 s) falls back to keyword rules. The complaint text is passed as data with fixed instructions,
and danger words (sparks, fire, gas...) can never be lowered below Critical.

## Escalation (feature 7)

Same code for the timer (`0 0 */6 * * *`) and the admin button. A complaint is escalated when it is past its deadline (**overdue**) or is **Critical** and open
over 6 hours. The `Escalations` table has a UNIQUE rule on (complaint, reason) and the insert only happens if the pair is new, so there are no duplicates even
if the timer and the button run together.

## Duplicate detection (feature 10)

Open complaints from the last 30 days are compared by shared words (Jaccard score) plus a bonus for the same location. Only a warning is shown; submission is never blocked.

## Speech (feature 9) and secrets

`SPEECH_KEY` lives only in the Function App settings. `GET /speech/token` (sign-in required) exchanges it for a 10-minute token. React gives that token to the Speech SDK.
No audio is stored by us. If speech is off or fails, the form shows a clear message and typing keeps working.

## Security summary

Argon2 password hashes and login lockout · JWT signed with a secret in app settings · role taken from the token, never from the request ·
students see only their complaints, staff only theirs, admin all · parameterized SQL · private blob container with 30-minute read links ·
uploads checked by content, random blob names · managed identity for SQL, Blob and Foundry (no passwords in code) · no secrets in React or git.

## API summary

| Endpoint | Who |
|---|---|
| `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | public / signed in |
| `GET /workspace` | any signed-in role (filtered by role) |
| `POST /ai/classify`, `POST /complaints/duplicates`, `GET /speech/token` | any signed-in role |
| `POST /complaints`, `POST /complaints/{ref}/feedback` | student (owner) |
| `POST /complaints/{ref}/assign` | admin |
| `POST /complaints/{ref}/status` | assigned staff, admin |
| `POST /complaints/{ref}/attachments` | the student, the assigned staff, admin |
| `GET /admin/analytics`, `POST /admin/escalation/run`, departments and categories CRUD | admin |
