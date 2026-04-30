# ScannerHT Project Context

## 1. Project Goal

ScannerHT is a crypto assistant with:

- a Telegram bot
- a web app
- a shared Python backend
- a shared SQLite database

Main UX goal:

- fast onboarding
- one active screen at a time
- shared user state between Telegram and web

## 2. Current Architecture

### Backend

- Python `FastAPI`
- main entry: `run_backend.py`
- API app: `backend/main.py`
- shared business logic: `backend/services.py`
- auth/session logic: `backend/auth.py`
- schemas: `backend/schemas.py`
- config: `backend/config.py`

### Web

- static web app served directly by FastAPI
- HTML: `web/index.html`
- CSS: `web/assets/styles.css`
- JS: `web/assets/app.js`

### Telegram Bot

- Node.js + Telegraf
- local entry: `app.js`
- deployable Railway entry: `bot/index.js`
- bot now talks to the Python API instead of reading SQLite directly

### Database

- SQLite shared by backend and bot
- local default path: `data/scannerht.sqlite`
- Railway production path via volume: `/data/scannerht.sqlite`

## 3. What Was Built, In Order

### Phase 1. Telegram onboarding

We started from a minimal JS file and built:

- Telegram onboarding flow
- single-message UX
- language selection
- market type
- trading style
- exact 3 coin selection
- welcome screen

### Phase 2. Persistence

We first used JSON storage, then replaced it with SQLite.

Important:

- SQLite is now the real storage
- JSON is no longer the main persistence strategy

### Phase 3. Telegram settings

We added:

- settings screen
- modify language
- modify market
- modify style
- modify tracked coins
- restart onboarding

### Phase 4. Intro / splash screen

We added a first official intro screen before onboarding:

- optional welcome media
- start button
- saved `intro_seen`

### Phase 5. Python backend

We introduced a Python backend to prepare:

- a web version
- a shared API
- a cleaner long-term architecture

### Phase 6. Web app

We added a web app served by FastAPI with:

- auth gate
- onboarding-like flow
- settings
- welcome screen

### Phase 7. Telegram web login

We added Telegram login on the web side:

- Telegram widget support
- backend verification of Telegram auth payload
- cookie session
- `/api/web/me`

### Phase 8. Market module MVP

We added a first Market module:

- backend route for market overview
- web dashboard for market view
- Telegram market screen

Current market mode:

- `live-coingecko` supported in production
- automatic fallback to `live-coinbase` if CoinGecko fails or rate-limits
- fallback to `modelled` if the live provider fails
- short cache layer added for live market snapshots
- live responses now expose source, cache state, and update timestamp
- stale live cache can be reused when the provider rate-limits

### Phase 9. Signals module MVP

We added a first Signals module:

- backend route for signals overview
- web Signals screen
- Telegram Signals screen
- shared signal generation built from the Market layer
- action-oriented signal payload with `next_action`, `top_symbol`, conviction, trigger, and size guidance
- `scannerht-bot` must be deployed from `bot/` because the repo root Railway config is for the Python backend
- GitHub repo: not configured / unknown

### Phase 10. TradingView web charts

We added a first TradingView web integration:

- focused TradingView chart on the Market screen
- focused TradingView chart on the Signals screen
- chart symbol follows the current top market/signal context
- lightweight official embed approach without changing backend architecture

### Phase 11. Alerts MVP

We added a first Alerts module:

- backend route for alerts overview
- web Alerts screen
- Telegram Alerts screen
- alerts derived from Market + Signals instead of static placeholders
- action-oriented alert payload with trigger price, priority, distance, thesis, and action note

### Phase 12. Alerts delivery flow

We extended Alerts into a first delivery workflow:

- per-user alert preferences now include `alerts_enabled` and `alerts_min_priority`
- the web Alerts screen can arm/disarm Telegram delivery and change minimum priority
- the Telegram Alerts screen can arm/disarm delivery and change minimum priority inline
- protected internal backend routes now expose alert delivery jobs and digest acknowledgements
- the Telegram bot now polls delivery jobs and acknowledges delivered digests
- Alerts now expose delivery status, last send time, and next eligible window
- urgent high-priority proximity can bypass the normal cooldown when the trigger becomes very close

### Phase 13. Scanner MVP

We added a first Scanner module:

- backend route for scanner overview
- web Scanner screen
- Telegram Scanner screen
- ranked scanner candidates built from Market + Signals + Alerts
- candidates now expose scanner score, urgency, trigger plan, invalidation, and alert readiness

### Phase 14. User level onboarding

We added a first user experience level profile step:

- users now choose a level: `beginner`, `medium`, or `pro`
- the level is requested early in onboarding, right after language
- the level is stored in the shared backend user state
- the level can be changed later from Settings in both web and Telegram

### Phase 15. Product clarity pass

We clarified the role of the main product screens before widening scope:

- `Market` is now framed as the context screen
- `Signals` is now framed as the decision screen
- `Scanner` is now framed as the watch-next queue
- `Alerts` is now framed as the return/reminder screen
- Telegram desk messages now adapt to the user level (`beginner`, `medium`, `pro`)
- web desk views now use clearer role/question copy and less repeated structure
- beginner bot mode now shows a shorter one-focus summary with a clearer next action

### Phase 16. Wider scanner universe

We widened Scanner carefully without turning the product into noise:

- `Market` and `Signals` still stay centered on the user's selected watchlist
- `Scanner` now ranks a broader curated universe beyond the 3 selected coins
- selected watchlist names keep a small ranking bonus so discovery does not feel random
- scanner candidates now show whether they come from the watchlist or from broader discovery
- bot beginner mode still shows only one main scanner focus despite the wider universe

### Phase 17. Profile-driven scanner depth

We made scanner depth a real product behavior tied to user profile:

- `beginner` users now see `3` scanner ideas
- `medium` users now see `5` scanner ideas
- `pro` users can choose how many scanner ideas to display
- the setting is now part of shared user state so bot and web can stay aligned
- this confirms the product direction: profile changes must affect the whole experience, not just wording

### Phase 18. Validated level product spec

We validated the level system as an official product behavior, not just a messaging preference:

- `Beginner` must stay simple, low-noise, and action-first
- `Medium` must stay guided and decision-oriented
- `Pro` must be denser, more technical, and more configurable
- `Beginner` Scanner shows `3` ideas
- `Medium` Scanner shows `5` ideas
- `Pro` Scanner is configurable
- `Beginner` Alerts should focus on `high` priority only
- `Medium` Alerts should focus on `medium + high`
- `Pro` Alerts should remain configurable
- the whole product should adapt by level: scanner depth, alerts noise, signal detail, and message density
- the next product priority is not PostgreSQL; it is to make bot/web feel much more beta-ready in strategy, structure, data, decisions, and presentation

### Phase 19. Level-aware Signals and Alerts behavior

We turned the validated level spec into real product behavior for `Signals` and `Alerts`:

- `Signals` now exposes only `1` setup for `beginner`, keeping the desk single-focus and action-first
- `Signals` still shows the full selected watchlist for `medium` and `pro`, but every setup now carries an explicit `invalidation`
- `Alerts` now enforce their effective minimum priority by level:
  - `Beginner` => `High` only
  - `Medium` => `Medium + High`
  - `Pro` => user-configurable
- the bot and web no longer expose alert-priority controls outside `pro`
- the `Scanner` still keeps its broader queue by level, but `alert_ready` now respects the effective alert threshold without hiding scanner candidates
- this step was verified locally with smoke tests and syntax checks; it still needs Railway redeploy to become production truth

### Phase 20. Telegram presentation redesign

We started the product-polish pass on Telegram before touching the web redesign:

- the bot desks now use short, explicit sections instead of long unstructured text blocks
- `welcome`, `help`, and `settings` now read more like a product control room than a raw config dump
- `Market`, `Signals`, `Scanner`, and `Alerts` now share a more consistent desk format:
  - desk header
  - level/profile snapshot
  - short action sections
  - denser playbook only for `pro` where relevant
- the Telegram `Help` screen is now real, not a placeholder callback
- this step was syntax-verified locally and still needs Railway redeploy to become production truth

### Phase 21. Web presentation redesign

We carried the same product-polish pass into the web app:

- `Welcome` now feels more like a control room, with role blocks for the four desks plus a profile strip
- `Settings` now surfaces profile behavior more clearly instead of looking like a flat option list
- the web now has a real `Help` screen instead of leaving that menu item as a placeholder
- desk headers now use stronger structure with explicit role, question, and next action cards
- the new web layout stays aligned with the level system instead of treating every user view the same
- this step was syntax-verified locally
- after the latest deploy turn, both Railway services were re-deployed successfully:
  - `scannerht-api` => `SUCCESS`
  - `scannerht-bot` => `SUCCESS`
- production `GET /api/health` still responds `{"status":"ok","database_backend":"sqlite","database_path":null}`
- the remaining gap is manual browser/Telegram validation of the redesigned presentation in production

### Phase 22. Environment-aware decision filter

We improved decision quality so the product reacts better to weak market environments:

- `Signals` now downshift weaker setups when the broader regime is `Defensive chop`
- `Signals` also downshift weaker setups when volatility is `Explosive`
- this makes `Active / Watch / Stand aside` more coherent with the overall market instead of looking only at the coin in isolation
- `Scanner` scoring now includes a regime-aware adjustment so defensive conditions do not rank weak ideas too optimistically
- local smoke tests confirmed the intended effect:
  - weak reclaim ideas were downgraded in defensive conditions
  - stronger names could still remain actionable if confidence stayed high enough
- this step was verified locally and is now re-deployed to Railway production
- production validation confirmed the new backend is live:
  - Railway `scannerht-api` deployment `cf204a0d-4e99-4af7-8703-6a261bb123d5` => `SUCCESS`
  - `GET /api/health` still responds cleanly
  - `GET /api/users/1536868565/signals` returned `Selective continuation` with `1 active / 1 watch / 1 stand aside`
  - `GET /api/users/1536868565/scanner` returned `3 hot / 3 building / 2 early`

### Phase 23. Telegram language-coherence pass

We tightened the Telegram bot so the selected language now drives much more of the visible environment instead of only changing a few labels:

- the onboarding language step now uses a neutral multilingual prompt before selection, then the rest of the flow continues in the selected language
- `English` now has the same Telegram `ui` layer as `French` and `Spanish`, removing a real presentation inconsistency
- Telegram chart labels, freshness labels, and more desk metrics now follow the selected language more consistently
- the alert-priority lock callback is now localized instead of always answering in English
- scanner wording now mixes less English into the French and Spanish environments
- this pass is syntax-verified locally with `node --check bot/index.js`
- this pass is not yet re-deployed to Railway production in this turn

### Phase 24. Stronger level-driven presentation

We tightened the difference between `Beginner`, `Medium`, and `Pro` so the level now changes more than just a few labels:

- `Signals` now reads more differently by level in both Telegram and web:
  - `Beginner` stays focused on one main action, conviction, and trigger
  - `Medium` stays guided with action, trigger, size, and invalidation
  - `Pro` stays denser with the fuller setup context
- `Alerts` now reads more differently by level in the web app:
  - `Beginner` focuses on top symbol, current delivery status, and high-priority-only behavior
  - `Medium` and `Pro` keep broader alert summaries
- `Scanner` is now much less dense for `Beginner` in both Telegram and web
- the web `Scanner` view now has genuinely different cards and summary blocks for `Beginner`, `Medium`, and `Pro`
- this pass keeps language and level as separate product axes:
  - language controls the text environment
  - level controls density, depth, and decision structure
- this pass is syntax-verified locally with:
  - `node --check bot/index.js`
  - `node --check web/assets/app.js`
- this pass is not yet re-deployed to Railway production in this turn

### Phase 25. Medium guidance pass

We pushed `Medium` closer to its intended product role: not minimal like `Beginner`, not dense like `Pro`, but clearly decision-guiding:

- `Signals` now highlights more decision-ready fields for `Medium` in both Telegram and web:
  - top symbol
  - conviction
  - trigger
  - size guidance
- `Alerts` now shows more decision-guiding fields for `Medium`, especially top trigger and trigger distance
- `Beginner` stays more compressed and less technical, especially in `Scanner`
- `Pro` keeps the denser context instead of losing information to match lower levels
- this keeps the product logic aligned with the current target maturity:
  - `Beginner` = one action, low noise
  - `Medium` = guided decision
  - `Pro` = denser control
- this pass is syntax-verified locally with:
  - `node --check bot/index.js`
  - `node --check web/assets/app.js`
- this pass is not yet re-deployed to Railway production in this turn

### Phase 26. FR level validation and web language polish

We validated the current level logic against the live Railway API using `FR + Beginner`, `FR + Medium`, and `FR + Pro`, then used that feedback to keep polishing the web:

- live production validation confirmed the level logic is behaving as intended on the backend:
  - `Beginner` => `signals.setups = 1`, `alerts delivery min priority = High`, `scanner visible_count = 3`
  - `Medium` => `signals.setups = 3`, `alerts delivery min priority = Medium`, `scanner visible_count = 5`
  - `Pro` => configurable scanner depth remained active, with `scanner visible_count = 8` in the validation run
- a second production pass confirmed the same structure after the latest deploy:
  - `FR + Beginner` => `top_symbol = ETH`, `signals.setups = 1`, `alerts.items = 1`, `scanner.visible_count = 3`
  - `FR + Medium` => `top_symbol = ETH`, `signals.setups = 3`, `alerts.items = 3`, `scanner.visible_count = 5`
  - `FR + Pro` => `top_symbol = ETH`, `signals.setups = 3`, `alerts.items = 3`, `scanner.visible_count = 8`
- the same production validation also confirmed the user profile stayed coherent during the test:
  - `language = fr`
  - `next_step = welcome`
- this backend-only gap has now been addressed in a later pass:
  - the live API now localizes core strategy sentences at the source for `fr`, so the French experience no longer depends only on the web/bot localization layer
  - live validation on Railway confirmed French payloads for `Signals`, `Alerts`, and `Scanner` across `FR + Beginner`, `FR + Medium`, and `FR + Pro`
  - examples confirmed live include French `headline`, `next_action`, `entry_trigger`, `delivery_note`, and scanner guidance strings
- after that validation, we tightened the web app so the visible environment is less mixed between French and English:
  - localized menu titles now exist in the web app instead of relying on English menu text
  - more generic desk labels now come from the selected language copy
  - more card labels now use localized terms for action, trigger, size, origin, chart labels, and scanner counts
  - `Help`, `Welcome`, and `Settings` now rely more on localized copy instead of hard-coded English phrasing
- we then extended that pass to the remaining web onboarding and chart framing:
  - setup badges and setup descriptions now follow the selected web language
  - the intro eyebrow and the TradingView framing text now follow the selected web language
  - the desk notes reuse the localization layer so the visible FR path is closer to fully French from start to finish
- we also added a small visual polish pass to the web cards and menu blocks so the UI feels more product-like and less flat
- a later polish pass pushed that visual layer further on both surfaces:
  - Telegram messages now use a cleaner section hierarchy with stronger headline/subtitle blocks instead of a flatter dump of sections
  - web cards now expose clearer visual tones for `Active / Watch / Stand aside`, alert priorities, scanner heat, and other card states
  - the web cards also gained stronger hover/border emphasis so the app feels closer to a real beta product than a static prototype
- the language pass then expanded beyond French:
  - live validation on Railway confirmed cleaner `ES` payloads for strategy text, including `lista de seguimiento`, `disparador`, and cleaner alert delivery wording
  - `EN` remained the native reference path while `ES` gained more complete source-level localization
- the strategy engine also became stricter in the same pass:
  - setup ranking now weighs trigger quality in addition to confidence
  - environment filtering now downgrades weaker ideas faster in `Defensive chop`, `Selective continuation`, and `Explosive` conditions
  - alert priority and scanner heat now respect trigger quality more directly, which reduces noisy ideas reaching end users
- runtime after this pass:
  - Railway API deployment `6b70792d-59f4-485c-9692-189f60d40504` => `SUCCESS`
  - Railway bot deployment `8bf8603f-9ff2-4c2f-8e5b-6f309c1b083d` => `SUCCESS`
- responsive and density pass:
  - the web UI was tightened for mobile and tablet with a smaller typography scale, reduced padding, more compact cards, and a shorter TradingView block on small screens
  - the goal of this pass was to reduce the current "zoomed" feeling on phones and improve first-screen density without flattening the desktop version
  - Telegram also received a small hierarchy polish so sections read faster on phone-sized screens
- stronger mobile density follow-up:
  - we added a second, more aggressive compactness pass after user feedback that the UI still felt too large and too zoomed on smaller screens
  - mobile browsers are now forced to keep the intended text scale through `text-size-adjust`, which helps avoid automatic text inflation on phones
  - the right-side preview card is now hidden on tablet/mobile widths so the main content gets more room instead of feeling compressed and oversized
  - typography, spacing, button sizing, and card radii were all tightened again across `980px`, `820px`, `640px`, and a new `480px` breakpoint
  - TradingView was shortened further on tablet and phone so the chart stops dominating the first screens
  - the public web shell now uses cache-busted asset URLs `tv2` to force the refreshed CSS/JS to load in browsers
- runtime after the responsive pass:
  - Railway API deployment `aa42ab33-4ee0-4ac5-9edd-a12262c16fa8` => `SUCCESS`
- runtime after the stronger density follow-up:
  - Railway API deployment `4021980b-3634-46e2-ae82-bfe7760f71cc` => `SUCCESS`
  - live HTML now serves `/assets/styles.css?v=20260315-tv2` and `/assets/app.js?v=20260315-tv2`
- this pass is syntax-verified locally with `node --check web/assets/app.js`
- the updated API/web service finished re-deploying successfully in this phase

### Phase 27. Deeper strategy-engine pass

We pushed the core decision engine deeper instead of only polishing the surface:

- `Signals`, `Alerts`, and `Scanner` now share a stronger internal hierarchy for setup quality instead of relying only on raw confidence and trigger quality in separate places
- the backend now computes two new internal concepts for each setup:
  - `setup_quality`, which rewards cleaner structure alignment, follow-through, and better archetypes
  - `noise_score`, which penalizes unstable volatility, weak alignment, fragile archetypes, and defensive market context
- the environment filter is now stricter with that shared logic:
  - weak or noisy setups are downgraded faster in `Defensive chop`
  - weak reclaims and unstable continuation ideas are downgraded faster in `Explosive`
  - `Risk-on` conditions still keep genuinely clean `Ready` setups actionable instead of flattening everything
- `Signals` now sort by a more meaningful hierarchy:
  - status first
  - setup quality second
  - lower noise before weaker/noisier ideas
  - trigger quality after that
- `Signals` size guidance now respects both setup quality and noise instead of only volatility
- `Alerts` now use the same quality/noise logic:
  - only cleaner active setups reach `High`
  - weaker active ideas can now stay `Medium` or even `Low`
  - reclaim alerts are more selective
  - noisy ideas get a wider trigger buffer so they do not look artificially urgent
- `Scanner` now uses the same shared hierarchy too:
  - score now rewards clean setup quality more directly
  - score now penalizes noisy setups instead of letting them rank too high on raw pulse alone
  - `Hot / Building / Early` now depend on quality + noise, not only distance and priority
  - weak `Stand aside + Low` discovery names can now be dropped from Scanner entirely when they add only noise
- local verification for this phase:
  - `python3 -m py_compile backend/*.py`
  - targeted smoke tests confirmed both sides of the intended behavior:
    - weak setups were downgraded harder in defensive / explosive examples
    - clean continuation examples still produced `Active / High / Hot`
- production verification for this phase:
  - Railway API health remained clean after deploy
  - production `Signals` returned a single clean French `top_symbol = SOL` with `ready_count = 3` and the visible setup staying `Actif`
  - production `Alerts` returned only one visible `Haute` priority item for that user, with `distance_percent = 0.35`
  - production `Scanner` returned `visible_count = 3`, `hot_count = 7`, `building_count = 1`, `early_count = 0`, with the visible top row led by `SOL`

### Phase 28. Market-type and trading-style hardening

We hardened the engine so `spot / futures` and `scalping / intraday` now change real decision logic instead of being mostly display context:

- the backend now has an explicit strategy profile layer per market/style pair
- that profile changes:
  - trigger floors
  - setup-quality floors
  - tolerated noise caps
  - alert priority thresholds
  - scanner filtering strictness
  - distance sensitivity and watchlist bonus
- asset classification is now more strategy-aware in both modelled and live market builders:
  - `spot` favors cleaner continuation structure more naturally
  - `futures` is stricter and can classify high-volatility names as `Fast momentum`
  - `scalping` raises the bar for ready entries and reduces tolerance for noisy setups
  - `intraday` stays more patient and more tolerant of slower continuation structure
- `Signals` now apply those market/style thresholds directly when deciding:
  - confidence is still important, but a futures-scalping setup now needs cleaner trigger quality and lower noise before it stays `Active`
  - size guidance is also more conservative in high-speed futures/scalping conditions
- `Alerts` now respect the same market/style logic:
  - `High` priority is harder to reach in `futures/scalping`
  - reclaim alerts are more selective in fast contexts
  - trigger buffers are still widened on noisy names so urgency is less fake
- `Scanner` now reacts to the same profile too:
  - scalping gives more weight to distance and trigger timing
  - futures penalizes noisy setups more aggressively
  - discovery names can be filtered out sooner in stricter contexts
- `Market` guidance is now also more coherent with the chosen mode:
  - `futures/scalping` gets a faster, tighter checklist
  - `spot/intraday` keeps more patient structure-oriented guidance
- local verification for this phase:
  - `python3 -m py_compile backend/*.py`
  - profile smoke tests confirmed:
    - `spot/intraday` still keeps clean active continuation setups
    - average `futures/scalping` contexts become much more selective
    - strong `futures/scalping` continuation examples still produce `Active / High / Hot`

## 4. Current API Surface

### Auth and web session

- `GET /api/web/config`
- `POST /api/auth/telegram`
- `POST /api/auth/logout`
- `GET /api/web/me`
- `PATCH /api/web/me`
- `POST /api/web/me/reset`

### Internal / bot user routes

- `GET /api/users/{user_id}`
- `PATCH /api/users/{user_id}`
- `POST /api/users/{user_id}/reset`

### Market

- `GET /api/web/market`
- `GET /api/users/{user_id}/market`

### Signals

- `GET /api/web/signals`
- `GET /api/users/{user_id}/signals`

### Alerts

- `GET /api/web/alerts`
- `GET /api/users/{user_id}/alerts`
- `GET /api/internal/alerts/jobs`
- `POST /api/internal/alerts/{user_id}/ack`

### Scanner

- `GET /api/web/scanner`
- `GET /api/users/{user_id}/scanner`

### Health

- `GET /api/health`

## 5. Current Web Auth Situation

The web app uses Telegram Login Widget.

What is already working:

- stable Railway public access
- Telegram login widget display
- Telegram confirmation flow
- backend auth payload verification
- session cookie creation
- authenticated web user session

Important:

- local `127.0.0.1` is not enough for proper Telegram web login
- a stable Railway domain is now configured in BotFather

## 6. Environment Variables In Use

Main `.env` values expected:

- `BOT_TOKEN`
- `BOT_USERNAME`
- `API_BASE_URL`
- `WELCOME_IMAGE_URL`
- `WELCOME_VIDEO_URL`
- `API_HOST`
- `API_PORT`
- `API_RELOAD`
- `MARKET_DATA_MODE`
- `MARKET_DATA_PROVIDER`
- `MARKET_DATA_CACHE_SECONDS`
- `SQLITE_PATH`
- `DATABASE_URL`
- `CORS_ORIGINS`
- `WEB_SESSION_SECRET`
- `WEB_SESSION_COOKIE`
- `WEB_SESSION_TTL_SECONDS`
- `WEB_SESSION_SECURE`
- `INTERNAL_API_KEY`
- `HEALTH_DETAILS_ENABLED`

## 7. How To Run The Project Right Now

### Web app only

Open terminal in project folder:

```bash
/tmp/scannerht-venv/bin/python run_backend.py
```

Then open:

- `http://127.0.0.1:8000` for local
- or `https://scannerht-api-production.up.railway.app` for the deployed app

### Telegram bot

In another terminal:

```bash
node app.js
```

### Public web access for local-only testing

In another terminal if needed:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Production does not need `cloudflared` anymore because Railway now provides the stable public URL.

## 8. What Logs Are Normal

These are normal:

- `GET /api/web/config 200`
- `GET /api/web/me 401` before login
- `GET / 200`
- `GET /assets/... 200`

This is also normal:

- `address already in use`

Meaning:

- another backend is already running on port `8000`

## 9. Current Important Limitation

Market is now live, but still early-stage.

Current state:

- the market layer can use live CoinGecko market snapshots in production
- Coinbase now acts as an automatic live fallback provider
- live snapshots are cached briefly to reduce external provider pressure
- live responses now include `data_provider`, `data_cached`, and `data_updated_at`
- stale cached live data can be reused if CoinGecko responds with rate limiting
- onboarding now includes a persistent user level profile step
- screen roles are now more explicit across web and Telegram
- bot desk summaries now adapt to the user's selected level
- beginner bot summaries are now intentionally shorter and less noisy
- scanner depth now changes with the selected user profile
- Signals now derives its setups from the Market layer
- Signals now returns a clearer execution plan with `next_action`, `top_symbol`, conviction, trigger, and size guidance
- Alerts can now be armed with a minimum priority threshold and a first delivery cadence
- Alerts now surface cooldown state and a more urgent delivery path for very close high-priority ideas
- Scanner now ranks candidates from the shared live/signal/alert context
- Scanner now scans a broader curated universe than the main 3-coin watchlist
- it falls back to modelled data if the live provider fails
- it is still not yet a full scanner engine, but there is now a usable first Scanner layer

## 10. Current Strategic Recommendation

Best next order:

1. keep improving product quality, decision logic, and user clarity before infra work
2. keep the four main screens clearly distinct in copy and usage
3. make profile-driven behavior visible across the whole bot and web experience
4. keep sharpening the level differences in `Signals` and `Alerts`, especially in visual hierarchy
5. manually validate the redesigned Telegram and web presentation in Railway production
6. keep improving strategy, structure, data quality, and decision support until the product feels beta-ready
7. continue product polish with real-user beta feedback on clarity and trust
8. move storage toward PostgreSQL last, after product beta quality is stronger

## 11. Public Test Readiness

Estimated readiness for a first public test:

- about `94%` for a limited public beta
- not yet ready for a broad public launch

What is already ready enough for public testing:

- stable Railway URL
- Telegram login works
- bot and web are both live
- live market data works with automatic Coinbase fallback
- onboarding now captures language + level + market + style + coins
- Signals now produce a clearer execution plan
- Alerts now produce watchable trigger levels and priorities
- Alerts can now be armed with Telegram delivery preferences
- Alerts now show delivery state and cooldown timing
- Scanner now produces ranked candidates in both web and Telegram
- Scanner now covers broader discovery while still distinguishing watchlist vs discovery ideas
- Scanner depth now changes by user profile, with pro-level configurability
- TradingView charts are visible in the web app
- the level system now has a validated product spec, not just a UI preference
- Signals and Alerts now behave more differently by level in the codebase
- the main screens now communicate more distinct roles
- Telegram summaries are now more beginner/pro aware through the shared level setting
- Telegram now has a more structured desk presentation plus a real Help screen
- the web now has a more structured control-room presentation plus a real Help screen
- decision quality is now more environment-aware in weak or explosive market regimes
- the newest environment-aware decision filter is now confirmed in Railway production
- the Telegram bot now has a stronger language-coherence pass in the local codebase
- the local codebase now has a stronger level-driven presentation pass across Telegram and web
- the local codebase now has a clearer `Medium` guidance pass across Telegram and web
- live Railway validation now confirms the FR level logic for Beginner, Medium, and Pro
- the local web codebase now has a broader language-polish pass plus a small visual polish pass

What is still missing before wider public exposure:

- manual production validation of the newest bot/web presentation and level-aware behavior
- Railway redeploy and production validation for the latest Telegram language-coherence pass
- Railway redeploy and production validation for the latest level-driven presentation pass
- Railway redeploy and production validation for the latest Medium guidance pass
- production validation of the latest web language-polish and visual-polish pass
- deeper Signals and alert automation quality
- more guided beginner copy refinement and real-user feedback on screen clarity
- stronger scanner discovery logic and future custom universe controls
- deeper visual polish on the web app once real usage feedback comes in
- even clearer visual separation between level modes inside Signals and Alerts
- PostgreSQL migration for a cleaner hosted data layer, after product beta quality is stronger
- more production monitoring and guardrails
- broader real-user flow testing across devices and sessions

## 12. Public URL Strategy Recommendation

Current public URL strategy is now Railway.

Current stable URL:

- `https://scannerht-api-production.up.railway.app`

Why it is the active strategy now:

- stable HTTPS URL
- no need to recreate a tunnel every session
- Telegram Login Widget already validated on this hostname
- better base for the next deployment steps

## 13. Railway Deployment Status

Current latest infra work:

- `railway.json` was added
- `RAILWAY_DEPLOY.md` was added
- backend now reads `PORT` automatically for hosted environments
- Railway CLI was installed locally
- Railway login completed successfully
- project `scannerht` created and linked locally
- service `scannerht-api` created and linked locally
- service `scannerht-bot` created and deployed
- Railway volume mounted at `/data`
- Railway public URL generated successfully
- BotFather domain updated successfully
- public healthcheck works on Railway

Current intended short-term deploy strategy:

- keep Python backend + web app on Railway
- keep Telegram bot on Railway as a separate worker service
- use the generated Railway URL for Telegram web login
- preserve SQLite with the mounted volume until PostgreSQL migration

Important storage note:

- SQLite is acceptable locally right now
- SQLite on Railway should only be used with a mounted volume
- the active volume mount path is `/data`
- `SQLITE_PATH=/data/scannerht.sqlite` is set on Railway
- long-term recommended database is PostgreSQL

## 14. Database Direction

Current database:

- SQLite in `data/scannerht.sqlite`

Current recommendation:

- keep SQLite for local development right now
- move to PostgreSQL soon after stable Railway deployment

Reason PostgreSQL is better long-term:

- more reliable for hosted multi-session usage
- cleaner future scaling
- safer long-term production path
- better fit for future live market, signals, and web growth

## 15. Most Recent Runtime Facts

Latest confirmed runtime facts:

- backend web login works with Telegram widget
- public Railway login worked
- `GET /api/web/me 401` is normal before login
- `Market` module exists in both web and Telegram
- `Signals` module now exists in both web and Telegram
- `Alerts` module now exists in both web and Telegram
- `Scanner` module now exists in both web and Telegram
- user level is now part of the shared profile state in both web and Telegram
- bot desk messages now adapt to the selected user level
- beginner Telegram desk messages now focus on one main item and one clear action
- `Market`, `Signals`, `Scanner`, and `Alerts` now present clearer product roles in the UI
- `Scanner` can now rank a broader universe and mark watchlist vs discovery ideas
- `Scanner` now respects profile depth: 3 for beginner, 5 for medium, configurable for pro
- Alerts now support per-user delivery arming and minimum priority selection
- internal alert delivery jobs are available through protected backend routes
- the bot service now polls delivery jobs and can acknowledge sent digests
- Alerts now expose delivery status, last send time, and next eligible delivery window
- urgent high-priority proximity can bypass the normal cooldown path
- Scanner responses now expose ranked candidates, urgency, trigger plan, invalidation, and alert readiness
- TradingView charts are now embedded in the web Market and Signals views
- live market responses now expose freshness metadata
- repeated market requests can be served from the short live cache
- Signals responses now expose `next_action`, `top_symbol`, conviction, trigger, and size guidance
- Alerts responses now expose trigger price, priority, distance, thesis, and action note
- internal bot routes are protected with an internal API key
- public health no longer exposes the Railway database path
- production CORS is tightened to the Railway origin
- local `GET /api/users/123456/signals` returned `200 OK` during pre-deploy verification
- production can stay live via Coinbase when CoinGecko rate-limits
- a newer Telegram language-coherence pass now exists locally in `bot/index.js`
- this local pass includes a multilingual pre-language prompt, localized chart wording, localized freshness labels, and a localized alert-priority lock message
- this local pass has been syntax-checked successfully with `node --check bot/index.js`
- this local pass is not yet deployed to Railway production
- a stronger level-driven presentation pass now also exists locally across `bot/index.js` and `web/assets/app.js`
- this local pass reduces technical density for `Beginner`, keeps `Medium` more guided, and leaves `Pro` denser
- this local pass has been syntax-checked successfully with:
  - `node --check bot/index.js`
  - `node --check web/assets/app.js`
- this local pass is not yet deployed to Railway production
- a Medium guidance pass now also exists locally across `bot/index.js` and `web/assets/app.js`
- this local pass makes Medium more decision-oriented in `Signals` and `Alerts` without turning it into Pro mode
- this local pass has been syntax-checked successfully with:
  - `node --check bot/index.js`
  - `node --check web/assets/app.js`
- this local pass is not yet deployed to Railway production
- live Railway API validation has now been run for `FR + Beginner`, `FR + Medium`, and `FR + Pro`
- the current validation confirmed:
  - `Beginner` => `1` signal setup, `High` alert threshold, `3` scanner ideas
  - `Medium` => `3` signal setups, `Medium` alert threshold, `5` scanner ideas
  - `Pro` => configurable scanner depth, validated at `8` visible ideas in the test
- a broader web language-polish pass now exists locally in `web/assets/app.js`
- a small web visual-polish pass now exists locally in `web/assets/styles.css`
- both local web passes have been syntax-checked successfully with `node --check web/assets/app.js`
- the refreshed API/web deployment is currently being pushed to Railway

Latest stable deployment facts:

- Railway CLI installed successfully
- Railway project: `scannerht`
- Railway service: `scannerht-api`
- Railway bot service: `scannerht-bot`
- Railway public URL: `https://scannerht-api-production.up.railway.app`
- Railway healthcheck returns `status=ok`
- `scannerht-bot` must be deployed from `bot/` with `--path-as-root` to avoid booting the Python backend by mistake
- Railway public health hides the database path in production
- Railway API hardened redeploy succeeded
- Telegram domain confirmation succeeded in BotFather
- bot service deployment succeeded on Railway
- Railway bot hardened redeploy succeeded
- Railway PostgreSQL service `Postgres` exists
- PostgreSQL schema has been initialized
- PostgreSQL contains the 2 users exported from SQLite
- Railway production Signals endpoint is deployed and reachable
- Railway production Alerts endpoint is deployed and reachable
- Railway production Market, Signals, and Alerts endpoints currently return `live-coinbase`
- Railway production Market endpoint supports `data_provider`, `data_cached`, and `data_updated_at`
- Railway production Signals endpoint now returns `next_action`, `top_symbol`, conviction, trigger, and size guidance
- Railway production Alerts endpoint now returns trigger price, priority, distance, thesis, and action note
- Railway web asset now serves the TradingView embed integration
- `MARKET_DATA_CACHE_SECONDS=300` is set for the Railway API service
- `scannerht-bot` was re-deployed from `bot/` after a wrong root deploy started the Python backend instead of the Telegram bot

## 16. Files That Matter Most

- `app.js`
- `run_backend.py`
- `backend/main.py`
- `backend/services.py`
- `backend/auth.py`
- `backend/schemas.py`
- `backend/config.py`
- `bot/index.js`
- `bot/package.json`
- `db/postgres_schema.sql`
- `scripts/export_users_json.py`
- `scripts/init_postgres.py`
- `scripts/import_users_postgres.py`
- `POSTGRES_PREP.md`
- `web/index.html`
- `web/assets/app.js`
- `web/assets/styles.css`
- `.env`
- `.env.example`
- `PROJECT_CONTEXT.md`

## 17. Reverse Snapshot: Current State Backward

Current latest state:

- web auth via Telegram works
- web app loads
- backend runs
- bot uses backend API
- bot is deployed on Railway
- Market module exists
- Market is live in production with CoinGecko fallback
- stable Railway URL is active
- Railway deployment is live
- Railway volume is mounted for SQLite persistence
- Telegram Login Widget is validated on Railway
- internal bot/backend traffic is protected with a shared key
- public API health is less verbose in production
- production CORS is narrowed to the deployed Railway origin
- PostgreSQL is now the recommended next database target after stable hosting

Before that:

- web app existed without Telegram auth
- bot and web shared SQLite through Python API

Before that:

- backend Python was introduced

Before that:

- Telegram bot used SQLite directly

Before that:

- Telegram onboarding and settings were built

Before that:

- project was only a minimal JS exercise file

## 18. Reusable Future Prompt

Use this in a future session if needed:

```text
We are continuing the ScannerHT project in /Users/dulorierjeanmario/Desktop/Class :JAVAScript, SQL, Python/Javascript/Exercices_1.

Current architecture:
- Python FastAPI backend in backend/
- Node Telegram bot with local wrapper in app.js and deploy entry in bot/index.js
- Static web app in web/
- Shared SQLite database in data/scannerht.sqlite

What already works:
- Telegram onboarding
- Telegram settings
- intro screen
- web app served by FastAPI
- Telegram web login with session cookies
- bot uses backend API
- first Market module exists
- Railway deployment is live
- Railway volume persists SQLite
- BotFather domain is already configured for Railway
- Telegram bot is deployed as a separate Railway service from `bot/`
- internal bot routes require a shared internal API key
- production health endpoint hides filesystem details
- PostgreSQL prep files exist for the next storage migration
- Railway PostgreSQL service is provisioned and seeded from SQLite
- Market data is live in production via CoinGecko with modelled fallback
- PostgreSQL init/import scripts are already available in the repo

Important current limitation:
- Market is still modelled, not connected to live data
- SQLite is still the current production storage, even if it is now persisted with a volume
- PostgreSQL is the recommended next database after Railway stabilization
- backend, web, and bot are all deployed; the next code migration is switching the repository layer from SQLite to PostgreSQL

Read PROJECT_CONTEXT.md first, then continue from the latest stable state without rebuilding what already exists.
```

## 19. Working Convention

Special shortcut requested by the user:

- when the user says `PROJECTCTX`, update `PROJECT_CONTEXT.md` with the latest stable project state before moving on

Current guidance about storage:

- SQLite is acceptable right now for the current stage and single-instance local development
- PostgreSQL is likely the right next database when deploying permanently, supporting more traffic, or moving beyond a single lightweight instance

## 20. Trade Engine v2

### Trade Lifecycle

Current simulated lifecycle chain:

- `Context -> Signal -> Alert -> TradePlan -> Events -> Journal -> Stats -> Adaptive Scoring`
- `Context -> Signal -> Alert -> TradePlan (persisted) -> simulate -> events -> update plan -> Journal -> Stats -> Adaptive Scoring`

This means the engine now goes beyond market narration and setup ranking:

- `Market` describes the environment
- `Signals` produces the setup decision
- `Alerts` turns setups into watch/return points
- `TradePlan` represents a simulated trade state
- `TradePlan (persisted)` can now be created first, then simulated against new price/state inputs
- `Trade Management Events` capture lifecycle milestones
- `Trade Journal` stores closed trade outcomes
- `Stats` aggregate performance
- `Adaptive Scoring` uses the journal as a lightweight non-ML feedback loop

### TradePlan

`TradePlan` now represents a simulated trade with:

- symbol
- direction (`long` / `short`)
- market_type
- trading_style
- entry price
- initial stop loss
- current stop loss
- `tp1`, `tp2`, `tpf`
- status
- risk fields
- timestamps

It also supports:

- dynamic stop-loss management
- `TP1 / TP2 / TPF` lifecycle
- account-based risk model

Current risk model fields:

- `account_equity`
- `risk_percent_per_trade`
- `risk_amount`
- `position_size`
- `stop_distance_percent`

### TradePlan Persistence & Simulation

TradePlan now has two dedicated internal flows:

- `POST /api/internal/trades/{user_id}/plans`
  - creates a persisted `TradePlan` in SQLite
  - server computes sizing fields such as `risk_amount`, `position_size`, and `stop_distance_percent`

- `POST /api/internal/trades/{user_id}/plans/{trade_id}/simulate`
  - simulation is based on an already persisted trade plan
  - `previous_plan = plan loaded from DB`
  - `current_plan = copy of the plan with simulated updates applied`
  - generated trade management events are linked to `trade_id`
  - the plan is updated in SQLite after simulation

This gives the engine a more stable lifecycle:

- create plan
- persist plan
- simulate new state
- emit events
- update plan
- journal / stats later

### Trade Management

Supported simulated trade management events:

- `tp1_hit`
- `tp2_hit`
- `tpf_hit`
- `sl_moved`
- `stopped`
- `invalidated`

Trade management currently uses:

- memory queue for fast runtime delivery
- SQLite persistence for backup + replay
- acknowledgement system to avoid repeated sends after confirmation

### Trade Journal

`TradeJournalEntry` currently stores:

- trade id
- symbol
- direction
- archetype
- market type
- trading style
- status (`open` / `closed`)
- entry / exit
- realized `R`
- TP hit count
- stopped-after-TP flag
- feedback label
- timestamps

Rules already enforced:

- `open` trades cannot define exit fields
- `closed` trades must define exit fields
- `closed_at >= created_at`

Current journal stats:

- `total_trades`
- `win_rate`
- `average_r_multiple`
- `average_tp_hit_count`
- `stopped_after_tp_rate`
- `performance_by_archetype`

Current limitations:

- no PostgreSQL persistence yet for this subsystem
- no public dashboard
- no live mark-to-market feed attached to every plan
- `current_price` can still be `null` in some debug responses

### Adaptive Scoring

Adaptive scoring MVP is now based on:

- `win_rate`
- `average_r_multiple`
- `feedback_label`
- `noise_score`

Current guardrails:

- archetype normalization is applied before stats/scoring
- minimum sample guardrail: fewer than `5` trades strongly reduces stats impact
- final adaptive score is clamped to `0..100`

This is intentionally:

- non-ML
- lightweight
- explainable
- suitable for early beta iteration

### Risk Model

Current per-trade risk model:

- `risk_amount = account_equity * risk_percent_per_trade / 100`
- `stop_distance_percent = abs(entry_price - initial_stop_loss) / entry_price * 100`
- `position_size = risk_amount / abs(entry_price - initial_stop_loss)`
- `realized_pnl_percent = realized_r_multiple * risk_percent_per_trade`
- `unrealized_pnl_percent = unrealized_r_multiple * risk_percent_per_trade`

Current futures/scalping guardrail:

- max `2%` risk per trade

Recommended product guidance:

- `beginner`: `0.25% -> 0.5%`
- `medium`: `0.5% -> 1%`
- `pro`: max `2%`

### Persistence

SQLite persistence now exists for:

- `trade_plans`
- `trade_journal`
- `trade_events`

Current sync model:

- trade events are written to memory queue + SQLite
- bot/job readers can replay pending events from SQLite
- acknowledgements update both queue state and DB state

### Internal Endpoints

Current internal trade endpoints:

- `/api/internal/trades/{user_id}/plans` `POST`
- `/api/internal/trades/{user_id}/plans`
- `/api/internal/trades/{user_id}/plans/{trade_id}/simulate`
- `/api/internal/trades/events`
- `/api/internal/trades/{user_id}/journal`

These are debug / internal-only endpoints and are not part of the public product API.

### Limitations Actuelles

- no PostgreSQL migration for trade engine tables yet
- no web dashboard for trade lifecycle yet
- no real order execution
- no exchange API integration
- no live continuous price tracking per trade plan
- `current_price` may still be `null` in some responses
