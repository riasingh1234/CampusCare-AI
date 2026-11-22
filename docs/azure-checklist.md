# Azure checklist: everything you create, grant, enter and run

Do the steps in order. Tick each box. **Nothing here is created for you.** Names in `<angle brackets>` are yours to choose or copy.
Pricing and free offers change: check the pricing page and set a **budget alert** in Cost Management first.

> The `az` commands in section 9 follow Microsoft's CLI as documented for Flex Consumption. If a flag is rejected by your CLI
> version, run the same command with `--help`. The portal can do every step too.

## 1. Create the resources (one resource group, five services)

- [ ] **Resource group** `rg-campuscare` in one region close to you (for example Central India).
- [ ] **Azure SQL Database** (free offer if your subscription shows "Apply offer", serverless, auto-pause on). Create the SQL server with
      **Microsoft Entra authentication** and make yourself the Entra admin. Networking: add your **client IP**, and tick
      **"Allow Azure services and resources to access this server"** (the Function App needs it).
- [ ] **Storage account** (Standard, LRS). Create a **private** container named `complaint-images` (public access disabled).
      The same account can be the Function App's storage account.
- [ ] **Microsoft Foundry resource + project + one model deployment** (a small chat model). Note the **deployment name**.
      Do this last: `AI_ENABLED` stays `false` until everything else works.
- [ ] **Azure AI Speech** resource (the free F0 tier is enough for a demo). From its **Keys and Endpoint** page copy **KEY 1** and the **Location/Region**.
- [ ] **Function App**, Flex Consumption, Python 3.12, **0 always-ready instances** (section 9 has the command).

Not used on purpose: Key Vault, Application Insights, AI Search, Content Safety, Computer Vision, Document Intelligence.

## 2. Permissions

| Who | Resource | What to grant |
|---|---|---|
| You | SQL database | `CREATE USER [you@college.edu] FROM EXTERNAL PROVIDER;` then add `db_datareader`, `db_datawriter`, `db_ddladmin` (commands in `azure-setup.md` section 4) |
| You | Storage account | role **Storage Blob Data Contributor** |
| You | Foundry resource | role **Foundry User** (older portal name: Azure AI User) |
| Function App identity | SQL database | run **`database/grant_access.sql`** (replace the name placeholder first) |
| Function App identity | Storage account | role **Storage Blob Data Contributor** (also lets it create the temporary image links) |
| Function App identity | Foundry resource | role **Foundry User** |

First turn the Function App's identity on: Function App > Identity > System assigned > **On** (or `az functionapp identity assign`).
Role changes can take a few minutes. Speech uses a key, not a role (see below).

## 3. Settings (environment variables)

Local: `backend/local.settings.json`. Azure: Function App > Settings > **Environment variables** (application settings).
React: only `VITE_API_BASE_URL` in `frontend/.env`.

| Setting | Required | Where to get it | Secret? |
|---|---|---|---|
| `APP_ENV` | no | `local` on your PC, `production` in Azure | no |
| `ALLOWED_ORIGIN` | yes | The frontend address: `http://localhost:5173` | no |
| `JWT_SECRET` | yes | You generate it: `python -c "import secrets; print(secrets.token_urlsafe(48))"` | **yes** |
| `JWT_EXPIRY_MINUTES` | no | default `60` | no |
| `SQL_SERVER` | yes | SQL server > Overview > Server name (`name.database.windows.net`) | no |
| `SQL_DATABASE` | yes | the database name | no |
| `BLOB_ACCOUNT_URL` | yes | Storage account > Endpoints > Blob service | no |
| `BLOB_CONTAINER_NAME` | yes | `complaint-images` | no |
| `AI_ENABLED` | yes | `false` until Foundry works, then `true` | no |
| `AI_AUTH_MODE` | no | `entra` (default). `api_key` only as a fallback | no |
| `AI_FOUNDRY_PROJECT_ENDPOINT` | when AI on | Foundry portal > project home > project endpoint | no |
| `AI_FOUNDRY_DEPLOYMENT` | when AI on | Foundry > Models + endpoints > deployment **name** | no |
| `AI_FOUNDRY_RESOURCE_ENDPOINT`, `AI_FOUNDRY_API_KEY` | only for `api_key` mode | Foundry resource keys page | **key is secret** |
| `SPEECH_ENABLED` | yes | `false` until Speech works, then `true` | no |
| `SPEECH_REGION` | when speech on | Speech resource > Keys and Endpoint > Location, lowercase, no spaces (`centralindia`) | no |
| `SPEECH_KEY` | when speech on | Speech resource > Keys and Endpoint > KEY 1 | **yes** |
| `AZURE_CLIENT_ID` | no | leave empty (system-assigned identity) | no |
| `SEED_DEMO_PASSWORD` | for `init_db.py` | You choose, for example `Demo@1234`. Only a terminal variable, never an app setting | no |

Azure sets `AzureWebJobsStorage` and the runtime settings itself on Flex Consumption: do not add them. Locally the example file already
has `AzureWebJobsStorage=UseDevelopmentStorage=true`, which needs Azurite running (`npx azurite --silent --location .azurite`).

## 4. Prepare the database (from your computer)

```bash
cd backend && python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp local.settings.example.json local.settings.json                   # fill in the values from section 3
az login
python scripts/check_config.py
export SEED_DEMO_PASSWORD='Demo@1234'                                # PowerShell: $env:SEED_DEMO_PASSWORD='Demo@1234'
python scripts/init_db.py --demo-users                               # type yes when it shows your server and database
python scripts/seed_demo_complaints.py                               # optional sample complaints; type yes
```
Then run `database/grant_access.sql` for the Function App (after the Function App exists and its identity is on).

## 5. Run everything locally (against your real Azure resources)

```bash
# terminal 1 (backend folder, venv active)
npx azurite --silent --location .azurite
# terminal 2 (backend folder, venv active)
func start
# terminal 3
cd frontend && npm install && cp .env.example .env && npm run dev        # open http://localhost:5173
```

## 6. Switch on Foundry, then Speech

1. Foundry: set `AI_ENABLED=true` and the two `AI_FOUNDRY_*` values, restart `func start`.
   Test: in a student's "Report an issue" form type a leak description. The suggestion card should say **"Suggested by Azure AI Foundry"**.
   If it says "Suggested by simple rules", Foundry failed and the fallback worked: check the `func start` log for the warning.
2. Speech: set `SPEECH_ENABLED=true`, `SPEECH_REGION`, `SPEECH_KEY`, restart. Use **Chrome or Edge on http://localhost:5173** (microphone access needs localhost or https).

## 7. Demo test plan (what to click, what you should see)

| # | Do this | Expected result | Feature |
|---|---|---|---|
| 1 | Sign in as the student, open **Report an issue**, type "The ceiling fan threw sparks" in the description | Suggestion card shows category Electrical, priority **Critical** | 2, 3 |
| 2 | Type a description similar to an existing open complaint | "Possible duplicate" card lists it with a % and the Submit button still works | 10 |
| 3 | Click **Speak your complaint**, allow the microphone, speak a sentence, click Stop | Text appears in the description box and can be edited | 9 |
| 4 | Click the microphone, **block** the permission | Amber message explains how to allow it or to type instead | 9 |
| 5 | Attach a photo and submit | Success page with `CC-2026-xxxx`; the detail page shows the photo | 1, 4 |
| 6 | Sign in as admin, open the complaint, assign department, staff and priority | Status becomes **Assigned**, history shows the entry | 5, 6 |
| 7 | Sign in as that staff member, open the task, set **In Progress**, then **Resolved** with a note | Student sees the new status and the activity timeline | 6 |
| 8 | Student rates the resolved complaint | Stars saved, shows in analytics rating | 6, 8 |
| 9 | Admin overview: **Run check now** | Shows how many were checked / newly escalated. Press it again: **0 new**, nothing duplicated | 7 |
| 10 | Admin **Analytics** | Counts, status, priority, category charts and the department table match the data | 8 |
| 11 | Set `SPEECH_ENABLED=false` and restart | The microphone shows "Voice input is off. Please type your complaint." Typing still works | 9 |
| 12 | Set `AI_ENABLED=false` (or break the Foundry deployment name) | Suggestions still appear, labelled as simple rules | 3 |
| 13 | After deploying: Function App > Functions > `escalation_timer` > Monitor | A run appears every 6 hours (00:00, 06:00, 12:00, 18:00 UTC) | 7 |

## 8. Things to know

- Free SQL serverless pauses when idle; the first request after a pause can fail or be slow. Retry once.
- Close SQL tools (Query editor, SSMS) when not in use, or the database cannot auto-pause.
- Voice is sent straight from the browser to Azure Speech. Our server never receives audio, and nothing is recorded.
- The `Notifications` table exists in the schema but is not used: escalations show as an **Escalated** tag and a timeline entry instead.
- The React app runs locally for evaluation. If you host it later, add its address to `ALLOWED_ORIGIN` and the Function App's CORS list.

## 9. Deploy the backend to Azure (Flex Consumption, Python 3.12, 0 always-ready)

```bash
RG=rg-campuscare ; APP=<globally-unique-function-app-name> ; STORAGE=<your-storage-account> ; REGION=<for example centralindia>

az functionapp create --resource-group $RG --name $APP --storage-account $STORAGE \
  --flexconsumption-location $REGION --runtime python --runtime-version 3.12
az functionapp identity assign --resource-group $RG --name $APP        # then grant the roles from section 2

az functionapp config appsettings set --resource-group $RG --name $APP --settings \
  APP_ENV=production ALLOWED_ORIGIN=http://localhost:5173 JWT_SECRET='<your-secret>' \
  SQL_SERVER=<server>.database.windows.net SQL_DATABASE=<database> \
  BLOB_ACCOUNT_URL=https://<storage>.blob.core.windows.net BLOB_CONTAINER_NAME=complaint-images \
  AI_ENABLED=false SPEECH_ENABLED=false

az functionapp cors add --resource-group $RG --name $APP --allowed-origins http://localhost:5173

cd backend && func azure functionapp publish $APP
curl https://$APP.azurewebsites.net/api/health
```
Later add the Foundry and Speech settings the same way (`SPEECH_KEY` only as an application setting) and set `AI_ENABLED` / `SPEECH_ENABLED` to `true`.
Point the frontend at it: in `frontend/.env` set `VITE_API_BASE_URL=https://<APP>.azurewebsites.net/api`.
Always-ready instances stay at their default of **0**: do not set any.
