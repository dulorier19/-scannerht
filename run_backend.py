import os

if os.getenv("SERVICE_MODE") == "bot" or os.getenv("RAILWAY_SERVICE_NAME") == "scannerht-bot" or (
    os.getenv("API_BASE_URL") and os.getenv("BOT_TOKEN") and os.path.exists("bot/index.js")
):
    os.execvp("node", ["node", "bot/index.js"])

import uvicorn

from backend.config import API_HOST, API_PORT, API_RELOAD


if __name__ == "__main__":
    # Railway injects PORT for the public service; bind on all interfaces there
    # even if a local .env still contains API_HOST=127.0.0.1.
    host = "0.0.0.0" if os.getenv("PORT") else API_HOST
    uvicorn.run("backend.main:app", host=host, port=API_PORT, reload=API_RELOAD)
