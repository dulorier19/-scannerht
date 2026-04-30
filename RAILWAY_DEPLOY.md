# Railway Deploy Notes

## Goal

Deploy ScannerHT with a stable public URL without needing a personal domain first.

Railway provides:

- stable public HTTPS URL
- no need to keep `cloudflared` running
- better base for Telegram web login

## Current deploy target

This repo is prepared to deploy the Python backend and serve:

- web app
- API
- Telegram web auth endpoints
- Telegram bot as a separate Railway service from the `bot/` directory

The start command is defined in `railway.json`.

## Before deploy

Make sure `.env` values exist locally first:

- `BOT_TOKEN`
- `BOT_USERNAME`
- `WEB_SESSION_SECRET`

## Railway high-level steps

1. Create a Railway project.
2. Connect this GitHub repo or deploy from local with Railway CLI.
3. Railway will use `railway.json`.
4. In service settings, generate a public domain.
5. Copy the stable Railway URL.
6. Use that URL for Telegram web login.

## Railway CLI flow

If you deploy from local, the simplest sequence is:

1. install Railway CLI and log in
2. from this project folder, run `railway init`
3. create a new empty project when Railway asks
4. link this folder to the created service
5. run `railway up`

`railway.json` is already present in this repo, so Railway should pick up:

- build with Railpack
- start with `python run_backend.py`
- healthcheck on `/api/health`

## Bot service on Railway

The Telegram bot is deployed as a separate Railway service named `scannerht-bot`.

To avoid conflicts with the Python backend service, the bot deploys from the `bot/`
subdirectory instead of the repo root.

Important:

- do not run `railway up -s scannerht-bot` from the repo root
- the repo root contains `railway.json` for the Python backend
- if you deploy the bot from the root, Railway can start `python run_backend.py` instead of the Telegram bot

Useful command:

```bash
railway up bot --path-as-root -s scannerht-bot
```

The `bot/` folder now also contains its own `railway.json` with `node index.js` as the
start command, so the bot service keeps the correct entrypoint when deployed from
`bot/`.

Required bot variables on Railway:

- `BOT_TOKEN`
- `API_BASE_URL=https://scannerht-api-production.up.railway.app/api`
- `INTERNAL_API_KEY`

Optional:

- `WELCOME_IMAGE_URL`
- `WELCOME_VIDEO_URL`

## Volume for SQLite

This app stores data in SQLite. The backend reads `SQLITE_PATH` if defined; otherwise it
falls back to `data/scannerht.sqlite`.

For Railway, use a volume so the database survives redeploys and restarts:

1. open the Railway service
2. add a volume
3. mount it to a path such as `/data`
4. set `SQLITE_PATH=/data/scannerht.sqlite`
5. redeploy

Why this matters:

- without a volume, SQLite data can be lost on redeploy
- with `SQLITE_PATH=/data/scannerht.sqlite`, the app writes into persistent storage

Do not point `SQLITE_PATH` at a temporary path.

## Railway variables to define

In Railway service variables, set:

- `BOT_TOKEN`
- `BOT_USERNAME`
- `SQLITE_PATH=/data/scannerht.sqlite`
- `WEB_SESSION_SECRET`
- `WEB_SESSION_COOKIE`
- `WEB_SESSION_TTL_SECONDS`
- `WEB_SESSION_SECURE=true`
- `INTERNAL_API_KEY`
- `CORS_ORIGINS=https://scannerht-api-production.up.railway.app`
- `HEALTH_DETAILS_ENABLED=false`

Optional:

- `WELCOME_IMAGE_URL`
- `WELCOME_VIDEO_URL`

If an optional variable is not needed on Railway, leave it undefined instead of creating
an empty secret-backed variable entry.

Do not set `API_HOST=127.0.0.1` on Railway.
If you define `API_HOST`, use `0.0.0.0`.

Security notes:

- internal bot routes now require `X-Internal-API-Key`
- public health should not expose filesystem details in production
- tighten `CORS_ORIGINS` to the real Railway origin instead of `*`

## Build troubleshooting

If Railway fails during the Railpack build with an error similar to:

`failed to solve: secret ID missing for "" environment variable`

the problem is usually in Railway service variables, not in Python or `mise`.

Check the Railway Variables UI and remove or fix any entry that has:

- a blank variable name
- a value sourced from a secret that was never selected
- an optional variable created as an empty secret reference instead of being omitted

After cleaning up the variables, trigger a new deploy.

## Important note about URL stability

Railway gives a stable generated domain for the service.

That means:

- no new tunnel URL every session
- no repeated BotFather domain change every time

## Telegram after deploy

After Railway gives you the public URL:

1. open BotFather
2. set the Telegram web login domain
3. use the Railway hostname

If BotFather asks for domain only, use hostname only.

Example:

`scannerht-api-production.up.railway.app`

If a full HTTPS origin is requested in a newer UI:

`https://scannerht-api-production.up.railway.app`

## Local vs Railway

Local:

- run backend with `/tmp/scannerht-venv/bin/python run_backend.py`
- use cloudflared only for temporary web login testing

Railway:

- no cloudflared needed
- stable hosted URL
- backend/web service: `scannerht-api`
- bot worker service: `scannerht-bot`
