# ScannerHT Architecture

ScannerHT is a Telegram-first crypto trading assistant. The current repository runs a Telegraf bot from `app.js` and centralizes most behavior in `bot/index.js`.

This document defines the target architecture for a production-grade scanner bot without breaking the current app.

## Current entry flow

```txt
app.js
└── bot/index.js
```

## Target architecture

```txt
scannerht/
├── app.js
├── package.json
├── .env.example
├── README.md
├── ARCHITECTURE.md
│
├── config/
│   ├── env.js
│   ├── coins.js
│   ├── telegram.js
│   └── scanner.js
│
├── bot/
│   ├── index.js
│   ├── commands/
│   ├── callbacks/
│   ├── keyboards/
│   └── messages/
│
├── api/
│   ├── client.js
│   ├── users.api.js
│   ├── market.api.js
│   ├── signals.api.js
│   ├── alerts.api.js
│   └── trades.api.js
│
├── core/
│   ├── scanner/
│   ├── market/
│   ├── signals/
│   ├── smc/
│   └── trades/
│
├── services/
├── database/
├── jobs/
├── i18n/
├── utils/
└── tests/
```

## Refactor phases

### Phase 1 — Safe foundation

Goal: add structure and configuration files without changing runtime behavior.

- Add `.env.example`
- Add `config/env.js`
- Add `config/coins.js`
- Add `api/client.js`
- Add documentation

### Phase 2 — Extract API layer

Goal: move API calls out of `bot/index.js`.

- `getUser` → `api/users.api.js`
- `saveUser` → `api/users.api.js`
- `getMarketOverview` → `api/market.api.js`
- `getSignalsOverview` → `api/signals.api.js`
- `getAlertsOverview` → `api/alerts.api.js`
- `getScannerOverview` → `api/scanner.api.js`
- alert/trade acknowledgements → `api/alerts.api.js` and `api/trades.api.js`

### Phase 3 — Extract Telegram UI

Goal: split Telegram commands, callbacks, keyboards and message formatters.

- onboarding commands
- menu commands
- settings callbacks
- scanner callbacks
- alerts callbacks
- message formatters

### Phase 4 — Extract i18n

Goal: move translations to separate files.

- `i18n/fr.js`
- `i18n/en.js`
- `i18n/es.js`
- `i18n/index.js`

### Phase 5 — Core scanner engine

Goal: isolate the decision logic from Telegram.

- market regime
- signal scoring
- scanner ranking
- SMC modules
- risk/invalidation rules

### Phase 6 — Production hardening

Goal: make the bot deployable and maintainable.

- Dockerfile
- health checks
- structured logging
- tests
- CI workflow
- persistent database migrations

## Design rule

Telegram must only be a delivery layer. The trading/scanner logic must live inside `core/`, and the API/business logic must live inside `services/` and `api/`.
