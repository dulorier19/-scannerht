import os
from pathlib import Path

import psycopg


BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "db" / "postgres_schema.sql"


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL is required.")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema_sql)
        connection.commit()

    print(f"Applied PostgreSQL schema from {SCHEMA_PATH}")


if __name__ == "__main__":
    main()
