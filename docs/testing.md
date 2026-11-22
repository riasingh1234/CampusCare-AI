# Testing report: what is verified where

**Locally verified** = automated tests that ran with no Azure resource (in-memory fakes for the database, Blob Storage, Foundry and the Speech token service).
**Needs Azure** = cannot be proven on a computer without your real resources; the code is written but has never talked to that service.

Run them yourself: `cd backend && python -m unittest discover -s tests -t .` (144 tests) and `cd frontend && npm test` (25 tests).

## Locally verified

| Area | What the tests prove |
|---|---|
| Classifier rules (3) | each category, safety words → Critical, wording that raises/lowers priority, no suggestion for vague text |
| Foundry + fallback (2, 3) | valid answer used; error, timeout, non-JSON, unknown category, bad priority and broken settings all fall back to rules; AI off never calls Foundry; Foundry cannot lower a danger word below Critical |
| Complaint APIs (1, 5, 6) | submit, validation messages, role checks, assignment rules (staff must belong to the department), status transitions, resolution note rule, feedback rules, each role sees only its own data, 401/403/404/409 cases |
| Attachments (4) | real file type from bytes, size/empty/count limits, random blob names, path-safe display name, no database row if the blob upload fails, links in the workspace |
| Duplicates (10) | similar open complaint found, resolved ignored, only recent ones compared, no personal data returned, submission never blocked |
| Escalation (7) | overdue and critical rules, resolved never escalated, second run adds nothing, manual button, admin-only |
| Analytics (8) | totals, open/resolved, overdue, escalated, average resolution time, within-target %, ratings, per-category, per-priority, per-department, 30-day trend with time-zone shift, empty data |
| Speech (9) | token endpoint: disabled → clear 503, success returns token not key, Azure unreachable/rejected → clean 503 without leaking the key, sign-in required; settings validation. Browser logic with a fake SDK and fake microphone: recognised text delivered, microphone blocked / missing, token errors, SDK load failure, Azure cancel errors, silence, stop twice |
| Frontend API integration | `api.js` (headers, errors, 401 sign-out, uploads) and the data mapping the screens rely on. Also run once, outside the shipped tests, by driving the real `api.js` against the real endpoint functions over HTTP with in-memory fakes: login, classify, submit, upload, duplicate, assign, status, feedback, analytics, escalation, CRUD (all passed) |
| Existing Stage 2 | the original 40 auth, config, security and SQL-script tests |
| Frontend build | every `.jsx`/`.js` file parses and all local imports resolve (checked with esbuild) |

## Needs your Azure resources (NOT verified)

| Item | Why it cannot be proven locally | How you verify it |
|---|---|---|
| Every SQL statement in `repositories/` and `database/*.sql` | Written for T-SQL; run only against fakes here | `init_db.py`, then the demo test plan in `azure-checklist.md` section 7 |
| Managed identity / `az login` access to SQL, Blob, Foundry | Needs real roles | Section 2 of the checklist, then `func start` |
| Blob upload and the temporary read links (user delegation SAS) | Needs a storage account | Test plan step 5 (photo visible on the detail page) |
| Foundry classification | Needs a model deployment; the SDK call is written to the documented API but never executed | Test plan step 1 (card says "Azure AI Foundry") |
| Azure AI Speech token and live recognition | Needs a Speech resource and a microphone | Test plan steps 3, 4, 11 |
| Timer trigger firing every 6 hours | Needs the deployed Function App | Test plan step 13 |
| Flex Consumption deployment and CORS | Needs your subscription | Checklist section 9 |
| React screens in a browser (layout, clicks) | No browser or npm registry in the build environment | Click through the test plan; the logic under the screens is covered above |

## Honest limits

- The sandbox this was built in could not install `pytest`-style packages, the Azure SDKs, React or Vite. The backend tests used tiny stand-ins for `azure.functions` and `argon2`
  (not shipped), and `npm install` / `npm run build` were not run. Run both test commands and `npm run build` on your machine first.
- There is no rate limiting on the API beyond login lockout.
