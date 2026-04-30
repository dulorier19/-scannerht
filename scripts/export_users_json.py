import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_PATH = BASE_DIR / "data" / "scannerht.sqlite"
OUTPUT_PATH = BASE_DIR / "data" / "users-export.json"


def main() -> None:
    if not SQLITE_PATH.exists():
        raise SystemExit(f"SQLite database not found: {SQLITE_PATH}")

    with sqlite3.connect(SQLITE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                user_id,
                intro_seen,
                language,
                market,
                trading_style,
                coins,
                onboarding_complete,
                active_message_id
            FROM users
            ORDER BY user_id
            """
        ).fetchall()

    users: list[dict[str, object]] = []
    for row in rows:
        user = dict(row)
        user["intro_seen"] = bool(user["intro_seen"])
        user["onboarding_complete"] = bool(user["onboarding_complete"])
        user["coins"] = json.loads(user["coins"] or "[]")
        users.append(user)

    OUTPUT_PATH.write_text(json.dumps(users, indent=2), encoding="utf-8")
    print(f"Exported {len(users)} users to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
