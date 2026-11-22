# Azure setup guide (detailed notes)

> The short, ordered list is **`azure-checklist.md`**. This file keeps the longer explanations and troubleshooting.

This guide explains which values the backend needs, where to find them in the Azure portal, and which permissions to grant.
**Nothing here creates resources.** It assumes you already have (or will create, yourself, in the portal) an Azure SQL
database, a Storage account, a Microsoft Foundry project with a deployed model, and later a Function App.

> **Never paste real values into a chat, a GitHub issue or a commit.** You will type them only into `backend/local.settings.json`
> on your own computer (git-ignored) and, later, into the Function App's settings in the Azure portal.

## 1. How sign-in works (no passwords)

The backend uses one identity for SQL, Blob Storage and Foundry:

| Where the code runs | Identity used | How you set it up |
|---|---|---|
| Your computer | The account you sign in with | `az login` |
| Azure Functions | The Function App's **managed identity** | Turn it on, then grant it roles (section 4) |

Same code, no keys. Azure SQL is **Entra-only** in this project: there is no SQL password setting.
The only secrets are `JWT_SECRET` (signs login tokens), `SPEECH_KEY` (Azure AI Speech, backend only) and, only if you choose the fallback, `AI_FOUNDRY_API_KEY`.

## 2. Install the tools (once)

- Python 3.11 or 3.12. Microsoft's Functions docs list ODBC Driver 18 for Python 3.11 and newer (Driver 17 for 3.10 and older), so stay on 3.11+.
- Azure CLI (`az`)
- Azure Functions Core Tools v4 (`func`)
- **Microsoft ODBC Driver 18 for SQL Server** (search Microsoft Learn for "Download ODBC Driver for SQL Server"). On macOS/Linux you also need unixODBC (`brew install unixodbc` on macOS).
- Optional for later (timer trigger): Azurite, the local storage emulator, because `AzureWebJobsStorage` is set to `UseDevelopmentStorage=true`.

## 3. Values you need and where to find them

| Setting | Where to find it |
|---|---|
| `SQL_SERVER` | Azure portal > your **SQL server** > Overview > **Server name** (looks like `name.database.windows.net`). Host name only: no `tcp:`, no port. |
| `SQL_DATABASE` | Your SQL server > **SQL databases**: the database's name. |
| `BLOB_ACCOUNT_URL` | **Storage account** > Settings > **Endpoints** > **Blob service** (`https://<account>.blob.core.windows.net`). |
| `BLOB_CONTAINER_NAME` | Storage account > Data storage > **Containers**. Keep it **private** (no anonymous access). Default in the template: `complaint-images`. |
| `AI_FOUNDRY_PROJECT_ENDPOINT` | Foundry portal > your project's **home page** > project endpoint (`https://<resource>.services.ai.azure.com/api/projects/<project>`). |
| `AI_FOUNDRY_DEPLOYMENT` | Foundry project > your deployed models list > the **Name** column (this is the deployment name, not the base model name). |
| `JWT_SECRET` | You generate it (below). Not from Azure. |
| `AZURE_CLIENT_ID` | Leave empty. Only needed if the Function App uses a *user-assigned* managed identity: then its **Client ID**. |
| `AI_ENABLED` | `false` until you have tested Foundry. When `false`, only the rule-based classifier will run. |
| `SPEECH_ENABLED`, `SPEECH_REGION`, `SPEECH_KEY` | Azure AI Speech resource > Keys and Endpoint (KEY 1 and Location). `SPEECH_ENABLED=false` until you have tested it. |

Optional API-key fallback for Foundry (only if Entra sign-in is not possible for you): set `AI_AUTH_MODE` to `api_key`, then
`AI_FOUNDRY_RESOURCE_ENDPOINT` (the Foundry resource's endpoint, `https://<resource>.services.ai.azure.com`) and `AI_FOUNDRY_API_KEY`
(from the resource's keys page in the Azure portal; labels may vary). Keep the key backend-only; in Azure enter it only as a Function App application setting, never in code or git.
Microsoft's `azure-ai-projects` SDK supports Entra ID only, so the fallback uses the standard `openai` client instead.

Generate `JWT_SECRET` on your machine and paste it straight into `local.settings.json`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 4. Permissions to grant (in the Azure portal)

You need two identities to have access: **you** (for local work) and the **Function App's managed identity** (once deployed).
You must be allowed to assign roles on those resources (for example Owner or User Access Administrator). If you are on a
college or student subscription and the buttons are disabled, ask whoever administers it. Role changes can take a few minutes to apply.

### Azure SQL
1. SQL server > **Microsoft Entra ID** (or "Microsoft Entra admin") > set an **admin** (yourself, for development).
2. SQL server > **Networking** > add your current client IP to the firewall so your computer can connect.
3. Database > **Query editor** (sign in with Entra) and run, replacing the names:

```sql
-- You, for local development (also able to create tables in the next stage)
CREATE USER [you@yourcollege.edu] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [you@yourcollege.edu];
ALTER ROLE db_datawriter ADD MEMBER [you@yourcollege.edu];
ALTER ROLE db_ddladmin  ADD MEMBER [you@yourcollege.edu];

-- The deployed app: run database/grant_access.sql instead (it also grants the permission to take the next complaint number).
```
The app identity gets read and write only, never schema-changing rights.

### Blob Storage
Storage account > **Access control (IAM)** > Add role assignment > **Storage Blob Data Contributor** for you and for the Function App's managed identity (this role also lets the app create the temporary image links).

### Microsoft Foundry
Foundry resource > **Access control (IAM)** > Add role assignment > **Foundry User** for you and for the Function App's managed identity.
(Microsoft recently renamed this role; older portal views and articles call it **Azure AI User**.) Data-plane access needs this role even if you are Owner.

## 5. Local setup: the commands

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp local.settings.example.json local.settings.json     # Windows: copy local.settings.example.json local.settings.json
# Now open local.settings.json in your editor and replace every <placeholder>.
az login
python scripts/check_config.py       # offline check: fix anything marked [FIX]
python -m unittest discover -s tests # config unit tests
func start                           # then open http://localhost:7071/api/health
```
`/api/health` checks configuration only. It does **not** prove your SQL, Blob or Foundry permissions work.
Those helpers (`backend/core/azure_clients.py`) are **untested against Azure** until you run the demo test plan in `azure-checklist.md`.

## 5b. Create the database tables (needs your Azure SQL database)

Only after `check_config.py` passes and your database user has the roles from section 4:

```bash
python scripts/init_db.py --demo-users     # asks you to confirm the server and database first
```
It creates the tables from `database/schema.sql`, loads departments and categories from `database/seed.sql`, and (with `--demo-users`)
creates a demo admin, six staff and four students. The demo password is either `SEED_DEMO_PASSWORD` (if you set that environment variable)
or a random one printed once in your terminal. It is not saved anywhere. Running it again is safe.

## 6. Deploying later (for reference, nothing to do yet)

- Create the Function App on **Flex Consumption** with 0 always-ready instances (why, and what to create when: `azure-resources-and-costs.md`).
- Function App > **Identity** > **System assigned** > On. This is the identity you grant the roles above.
- Function App > **Environment variables / Application settings**: add the same names as `local.settings.json`. Do not upload that file (`.funcignore` already excludes it).
- Enter `JWT_SECRET` (and the API key, if used) as application settings. They are encrypted at rest and never appear in git or in the frontend. Key Vault is deliberately not used, to stay within the five agreed services.
- Set the allowed CORS origin to your real frontend URL, not `*`.

## 7. Troubleshooting

| What you see | Likely cause and fix |
|---|---|
| `[FIX] ... still contains a placeholder` | You left a `<...>` value in `local.settings.json`. |
| `DefaultAzureCredential failed to retrieve a token` | Run `az login`, or the Function App identity is not enabled. |
| SQL error about the client IP not being allowed (40615) | Add your IP in the SQL server's Networking page. |
| SQL "Login failed for user ..." | The database user was not created (`CREATE USER ... FROM EXTERNAL PROVIDER`), or you are on the wrong database. |
| "Data source name not found" / driver error | ODBC Driver 18 is not installed (or the name in `SQL_ODBC_DRIVER` is different). |
| Blob or Foundry 403 / 401 | Missing role, or the role was assigned less than a few minutes ago. |
| Foundry 404 | `AI_FOUNDRY_DEPLOYMENT` is not the deployment name. |
| First request after a quiet period fails or is slow | A serverless/free Azure SQL database auto-pauses and takes a moment to wake. Retry once. |

## 8. Safety checklist

- [ ] `backend/local.settings.json` is not in git (`git status` should not list it; `check_config.py` also warns).
- [ ] No real value appears in any file other than your local `local.settings.json`.
- [ ] React only knows the public API URL (`VITE_API_BASE_URL`). Every `VITE_` variable is visible to anyone who opens the site.
- [ ] If a secret was ever committed, rotate it. Deleting the file is not enough.
