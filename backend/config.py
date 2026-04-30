import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
load_dotenv(BASE_DIR / ".env")

_raw_db_path = os.getenv("SQLITE_PATH")
if _raw_db_path:
    DB_PATH = Path(_raw_db_path)
    if not DB_PATH.is_absolute():
        DB_PATH = BASE_DIR / DB_PATH
else:
    DB_PATH = DATA_DIR / "scannerht.sqlite"

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT") or os.getenv("API_PORT", "8000"))
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
API_RELOAD = os.getenv("API_RELOAD", "false").lower() == "true"
MARKET_DATA_MODE = os.getenv("MARKET_DATA_MODE", "modelled").lower()
MARKET_DATA_PROVIDER = os.getenv("MARKET_DATA_PROVIDER", "binance").lower()
MARKET_DATA_CACHE_SECONDS = max(0, int(os.getenv("MARKET_DATA_CACHE_SECONDS", "300")))
ALERT_MIN_INTERVAL_SECONDS = max(0, int(os.getenv("ALERT_MIN_INTERVAL_SECONDS", "1800")))
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
WEB_SESSION_SECRET = os.getenv("WEB_SESSION_SECRET", BOT_TOKEN)
if WEB_SESSION_SECRET == BOT_TOKEN and BOT_TOKEN:
    import warnings
    warnings.warn(
        "WEB_SESSION_SECRET utilise BOT_TOKEN comme fallback. "
        "Définissez WEB_SESSION_SECRET dans votre .env pour sécuriser les sessions web.",
        stacklevel=1,
    )
WEB_SESSION_COOKIE = os.getenv("WEB_SESSION_COOKIE", "scannerht_session")
WEB_SESSION_TTL_SECONDS = int(os.getenv("WEB_SESSION_TTL_SECONDS", "86400"))
WEB_SESSION_SECURE = os.getenv("WEB_SESSION_SECURE", "false").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_BACKEND = "postgres" if DATABASE_URL else "sqlite"
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

_health_details_default = "false" if os.getenv("PORT") else "true"
HEALTH_DETAILS_ENABLED = os.getenv("HEALTH_DETAILS_ENABLED", _health_details_default).lower() == "true"

if os.getenv("PORT"):
    if not WEB_SESSION_SECRET:
        raise RuntimeError("WEB_SESSION_SECRET is required in hosted environments.")
    if BOT_TOKEN and WEB_SESSION_SECRET == BOT_TOKEN:
        raise RuntimeError("WEB_SESSION_SECRET must not reuse BOT_TOKEN in hosted environments.")
    if not INTERNAL_API_KEY:
        raise RuntimeError("INTERNAL_API_KEY is required in hosted environments.")
