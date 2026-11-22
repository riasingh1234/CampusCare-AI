# Azure resources: what to create, and when

Your five services: **Azure Functions, Azure SQL Database, Azure Blob Storage, Azure AI Foundry, Azure AI Speech.** Nothing else is needed. The step-by-step list is `azure-checklist.md`.
Nothing below has been created for you. Create each resource yourself, in the portal, **only when its stage starts**.

> Prices and free grants change. The facts below come from Microsoft Learn and the Azure pricing pages as of November 2026.
> Check the pricing page and set a **budget alert** in Cost Management before you create anything.

## Important: the "Consumption plan" is now the legacy plan

- Microsoft calls the Linux **Consumption** plan legacy. It is retiring on **30 September 2028**, no longer gets new features,
  and Python 3.12 is the last Python version it supports.
- For new serverless apps Microsoft recommends **Flex Consumption**. It also scales to zero and bills only while code runs.
  Always-ready instances default to **0**, which means no idle cost.
- Free grant listed on the pricing page for Flex Consumption: **250,000 executions and 100,000 GB-s per month per subscription**
  (it applies to pay-as-you-go style subscriptions; confirm how it applies to an **Azure for Students** subscription).

**Recommendation:** create the Function App on **Flex Consumption, 0 always-ready instances, Python 3.12**.
The code in this project does not depend on the plan, so you can change your mind without rewriting anything.
If your student subscription cannot create Flex Consumption (region or policy limits), tell me and we will choose the next-cheapest option together.

## When each resource is needed

| When | Resource | Why now | Cost notes |
|---|---|---|---|
| Stage 1-2 testing (now, optional) | **Resource group** + **Azure SQL server + database** | Run `init_db.py` and test the real queries | Try the **Azure SQL Database free offer** (General Purpose serverless): 100,000 vCore-seconds, 32 GB storage and 32 GB backup per month, free for the life of the subscription. Choose **"Auto-pause the database until next month"** so you are never billed. Whether your Student subscription can use the free offer is not confirmed: the portal will show an "Apply offer" button if it can. |
| Attachments stage | **Storage account** (Standard, locally redundant) + private container `complaint-images` | Image uploads. The same account can also hold the Function App's host files | Pennies at student scale. Keep public access off. |
| AI stage | **Microsoft Foundry resource + project + one model deployment** | Only when you switch `AI_ENABLED=true` | Billed per use. Pick a small model, set a spending alert, and keep `AI_ENABLED=false` until you test. |
| Speech | **Azure AI Speech** resource (free F0 tier) | Voice input. Only when you set `SPEECH_ENABLED=true` | Free tier has a small monthly audio allowance; enough for a demo. |
| Deployment stage | **Function App** (Flex Consumption) | Host the API and the timer | See above. Turn on its system-assigned identity, then grant the roles in `azure-setup.md`. |

Not on the list because they are not among your five services: Key Vault (so secrets live in application settings), Application Insights (optional; skip it if you want to stay strictly within the five services, at the cost of fewer logs), and any frontend hosting. **Decision for you:** the React app can run locally for demos, or be hosted somewhere free outside these five services. We should decide before the deployment stage.

## Keeping the database inside the free allowance

The free offer's 100,000 vCore-seconds are consumed whenever the database is awake, and serverless databases only pause after an idle period.
A timer that queries the database every few minutes would keep it awake all month and use the allowance in days.
So the escalation timer will be **configurable and infrequent** (planned default: every 6 hours, adjustable by a setting), and the admin dashboard can also trigger a check on demand.
Disconnect SQL tools (SSMS, Azure Data Studio, the portal query editor) when you are not using them: open sessions stop auto-pause.
Add the **"Free amount remaining"** metric alert described in the free-offer docs.

## Role assignments (summary, details in azure-setup.md)

| Resource | You (local) | Function App identity |
|---|---|---|
| Azure SQL | database user with read/write (+ `db_ddladmin` for setup) | read/write only |
| Storage | Storage Blob Data Contributor | Storage Blob Data Contributor |
| Foundry | Foundry User | Foundry User |
| Speech | none (uses a key held only by the backend) | none |

## Risks to check early

- **Entra admin and role assignment rights.** Student subscriptions sometimes lack permission to set an Entra admin on the SQL server or to assign roles. You will find out at the first SQL step. If blocked, tell me what the portal says and we will pick a path (we are not adding SQL passwords unless you decide to).
- **Regional limits.** Student subscriptions can restrict some regions and services.
