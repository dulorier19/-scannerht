import json
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Json


BASE_DIR = Path(__file__).resolve().parent.parent
IMPORT_PATH = BASE_DIR / "data" / "users-export.json"


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL is required.")

    if not IMPORT_PATH.exists():
        raise SystemExit(f"Import file not found: {IMPORT_PATH}")

    users = json.loads(IMPORT_PATH.read_text(encoding="utf-8"))
    if not isinstance(users, list):
        raise SystemExit("Import payload must be a list.")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for user in users:
                cursor.execute(
                    """
                    INSERT INTO users (
                        user_id,
                        intro_seen,
                        language,
                        market,
                        trading_style,
                        coins,
                        onboarding_complete,
                        active_message_id
                    )
                    VALUES (
                        %(user_id)s,
                        %(intro_seen)s,
                        %(language)s,
                        %(market)s,
                        %(trading_style)s,
                        %(coins)s,
                        %(onboarding_complete)s,
                        %(active_message_id)s
                    )
                    ON CONFLICT (user_id) DO UPDATE SET
                        intro_seen = EXCLUDED.intro_seen,
                        language = EXCLUDED.language,
                        market = EXCLUDED.market,
                        trading_style = EXCLUDED.trading_style,
                        coins = EXCLUDED.coins,
                        onboarding_complete = EXCLUDED.onboarding_complete,
                        active_message_id = EXCLUDED.active_message_id
                    """,
                    {
                        "user_id": user["user_id"],
                        "intro_seen": bool(user.get("intro_seen")),
                        "language": user.get("language"),
                        "market": user.get("market"),
                        "trading_style": user.get("trading_style"),
                        "coins": Json(user.get("coins", [])),
                        "onboarding_complete": bool(user.get("onboarding_complete")),
                        "active_message_id": user.get("active_message_id"),
                    },
                )
        connection.commit()

    print(f"Imported {len(users)} users from {IMPORT_PATH}")


if __name__ == "__main__":
    main()
