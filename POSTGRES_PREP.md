# PostgreSQL Preparation

## Goal

Prepare ScannerHT to move from SQLite to PostgreSQL without interrupting the current Railway deployment.

## What Is Already Prepared

- `DATABASE_URL` is now reserved in `.env.example`
- PostgreSQL target schema exists in `db/postgres_schema.sql`
- SQLite user export script exists in `scripts/export_users_json.py`
- PostgreSQL init script exists in `scripts/init_postgres.py`
- PostgreSQL import script exists in `scripts/import_users_postgres.py`

## Current Production Reality

- production still runs on SQLite
- SQLite is persisted on Railway with `/data/scannerht.sqlite`
- PostgreSQL is the next storage step, not the current runtime backend

## Current Preparation Status

- Railway PostgreSQL service `Postgres` exists
- `db/postgres_schema.sql` has been applied
- exported SQLite users have been imported into PostgreSQL
- PostgreSQL currently contains the same 2 users exported from SQLite

## Suggested Migration Order

1. create a Railway PostgreSQL service
2. copy its `DATABASE_URL`
3. export current SQLite users with:

```bash
python3 scripts/export_users_json.py
```

4. apply `db/postgres_schema.sql` to the PostgreSQL database
5. or initialize it with:

```bash
python3 scripts/init_postgres.py
```

6. import the exported users into PostgreSQL with:

```bash
python3 scripts/import_users_postgres.py
```

7. update backend data access layer to read/write PostgreSQL
8. test parity against the imported PostgreSQL data
9. switch production only after parity testing

## Important Note

`DATABASE_URL` is prepared in config, but the live app still uses SQLite until the repository layer is migrated.
