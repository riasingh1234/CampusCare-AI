# Database

- `schema.sql`: all tables, constraints and indexes (safe to run again).
- `seed.sql`: departments and categories (reference data only; no users, no passwords).

Run both with `python backend/scripts/init_db.py` (add `--demo-users` for demo accounts). It needs an Azure SQL database,
your `az login`, and a passing `python backend/scripts/check_config.py`. See `docs/azure-setup.md`.
The scripts have been syntax-checked locally but **not yet executed against Azure SQL**.
