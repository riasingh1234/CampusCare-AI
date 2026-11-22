# Backend (Python Azure Functions v2)

```
backend/
  function_app.py              # app entry: registers the blueprints below, GET /api/health (config check only)
  host.json  .funcignore  requirements.txt  local.settings.example.json
  api/                         # HTTP endpoints: read input, call a service, return JSON
    auth.py                    #   POST /auth/register /auth/login   GET /auth/me
    complaints.py              #   GET /workspace  POST /ai/classify /complaints/duplicates /complaints
                               #   POST /complaints/{ref}/assign|status|feedback|attachments
    admin.py                   #   GET /admin/analytics  POST /admin/escalation/run  departments + categories CRUD
    speech.py                  #   GET /speech/token
  timers/escalation.py         # Timer trigger, every 6 hours
  services/                    # the rules (plain functions)
    classifier.py  duplicates.py  complaint_service.py  escalation.py  analytics.py  blob_storage.py  speech.py  auth_service.py
  repositories/                # ALL SQL, parameterized: complaints.py  reference.py  users.py
  core/                        # config, Azure client helpers, security, validation, errors
  scripts/                     # check_config.py  init_db.py  seed_demo_complaints.py
  tests/                       # unit tests with in-memory fakes (no Azure needed)
```

Endpoint table with who may call each: `../docs/architecture.md`. Settings: `../docs/azure-checklist.md`.

```bash
python -m unittest discover -s tests -t .     # run all tests
python scripts/check_config.py                # check local.settings.json
func start                                    # run the API locally (needs Azurite or a real storage connection string for the timer)
```
