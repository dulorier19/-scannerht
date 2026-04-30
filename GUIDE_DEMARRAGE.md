 # 🚀 Guide de démarrage — ScannerHT

Guide étape par étape pour connecter et faire partir le bot, en local et en production.

---

## Phase 1 — Prérequis

### 1.1 Outils requis

| Outil | Version min. | Vérification |
|-------|-------------|--------------|
| Node.js | 18+ | `node --version` |
| Python | 3.11+ | `python3 --version` |
| npm | 9+ | `npm --version` |
| pip | 23+ | `pip3 --version` |

### 1.2 Obtenir un token Telegram

1. Ouvrir Telegram → chercher **@BotFather**
2. Envoyer `/newbot`
3. Choisir un nom et un username (ex: `vawmabot`)
4. Copier le **BOT_TOKEN** retourné (format : `7797920745:AAE...`)

---

## Phase 2 — Configuration locale

### 2.1 Installer les dépendances

```bash
# Depuis la racine du projet
cd "/Users/dulorierjeanmario/Desktop/Class :JAVAScript, SQL, Python/Javascript/Exercices_1"

# Dépendances Python (backend)
pip3 install -r requirements.txt

# Dépendances Node.js (bot)
cd bot && npm install && cd ..
```

### 2.2 Configurer le `.env`

Vérifier que le fichier `.env` à la racine contient au minimum :

```env
# ═══════════════ OBLIGATOIRES ═══════════════
BOT_TOKEN=ton_token_telegram_ici
BOT_USERNAME=vawmabot
INTERNAL_API_KEY=une_cle_longue_aleatoire

# ═══════════════ BACKEND LOCAL ═══════════════
API_BASE_URL=http://127.0.0.1:8000/api
API_HOST=127.0.0.1
API_PORT=8000

# ═══════════════ SESSION WEB ═══════════════
WEB_SESSION_SECRET=un_secret_different_du_bot_token
```

> ⚠️ **IMPORTANT :** `WEB_SESSION_SECRET` ne doit PAS être identique à `BOT_TOKEN`.

---

## Phase 3 — Lancer en local (2 terminaux)

Le projet fonctionne avec **2 services séparés** qui communiquent par HTTP :

```
┌──────────────┐     HTTP (fetch)     ┌──────────────┐
│  Bot Telegram │ ──────────────────► │  Backend API  │
│  (Node.js)    │                     │  (FastAPI)    │
│  port: aucun  │                     │  port: 8000   │
└──────────────┘                     └──────────────┘
       ↕                                    ↕
   Telegram API                        SQLite DB
```

### 3.1 Terminal 1 — Démarrer le backend

```bash
cd "/Users/dulorierjeanmario/Desktop/Class :JAVAScript, SQL, Python/Javascript/Exercices_1"
python3 run_backend.py
```

**Résultat attendu :**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started reloader process
```

**Vérification :** Ouvrir `http://127.0.0.1:8000/api/health` dans un navigateur.
Réponse attendue :
```json
{"status": "ok", "database_backend": "sqlite", "database_path": "data/scannerht.sqlite"}
```

### 3.2 Terminal 2 — Démarrer le bot

```bash
cd "/Users/dulorierjeanmario/Desktop/Class :JAVAScript, SQL, Python/Javascript/Exercices_1"
node bot/index.js
```

**Résultat attendu :**
```
Alert delivery polling every 300000ms.
ScannerHT bot is running. Press Ctrl+C to stop.
```

### 3.3 Tester le bot

1. Ouvrir Telegram
2. Chercher ton bot par son username (`@vawmabot`)
3. Envoyer `/start`
4. Le flow d'onboarding doit apparaître (intro → langue → niveau → marché → style → coins)

---

## Phase 4 — Diagnostic des erreurs courantes

### ❌ `BOT_TOKEN is missing`
```
→ Le .env n'est pas chargé ou BOT_TOKEN est vide
→ Vérifier que .env est à la racine du projet
```

### ❌ `API request failed (connection refused)`
```
→ Le backend n'est pas démarré
→ Lancer python3 run_backend.py d'abord (Terminal 1)
```

### ❌ `API request failed (403)`
```
→ INTERNAL_API_KEY ne correspond pas entre bot et backend
→ Les deux lisent le même .env, donc ça devrait matcher en local
→ Vérifier qu'il n'y a pas un .env différent dans bot/
```

### ❌ `AbortError: The operation was aborted` (nouveau)
```
→ Le backend met plus de 10s à répondre
→ Augmenter API_FETCH_TIMEOUT_MS=20000 dans .env
```

### ❌ `SQLITE_ERROR: no such table`
```
→ Le backend crée la DB au premier lancement
→ Relancer python3 run_backend.py
```

### ❌ `WEB_SESSION_SECRET must not reuse BOT_TOKEN`
```
→ Tu es en mode hosted (PORT défini) mais WEB_SESSION_SECRET = BOT_TOKEN
→ Définir un secret différent dans .env
```

---

## Phase 5 — Déployer sur Railway (production)

### 5.1 Architecture Railway

```
Railway Project
├── Service: scannerht-api (Python backend)
│   ├── railway.json → python run_backend.py
│   ├── Volume monté → /data (SQLite persistant)
│   └── URL publique → scannerht-api-production.up.railway.app
│
└── Service: scannerht-bot (Node.js bot)
    ├── bot/railway.json → node index.js
    ├── Pas de volume (stateless)
    └── Pas d'URL publique (worker)
```

### 5.2 Déployer le backend

```bash
# Installer Railway CLI
npm install -g @railway/cli
railway login

# Initialiser le projet
railway init
# Choisir: "Create new project"

# Déployer
railway up
```

### 5.3 Configurer les variables Railway (backend)

Dans Railway → Service → Variables :

| Variable | Valeur |
|----------|--------|
| `BOT_TOKEN` | ton token |
| `BOT_USERNAME` | vawmabot |
| `SQLITE_PATH` | `/data/scannerht.sqlite` |
| `WEB_SESSION_SECRET` | un secret long et unique |
| `WEB_SESSION_SECURE` | `true` |
| `INTERNAL_API_KEY` | une clé longue aléatoire |
| `CORS_ORIGINS` | `https://scannerht-api-production.up.railway.app` |
| `HEALTH_DETAILS_ENABLED` | `false` |

> ⚠️ **Ajouter un Volume** : monter sur `/data` pour que SQLite survive aux redéploiements.

### 5.4 Déployer le bot

```bash
railway up bot --path-as-root -s scannerht-bot
```

Variables Railway du bot :

| Variable | Valeur |
|----------|--------|
| `BOT_TOKEN` | même token |
| `API_BASE_URL` | `https://scannerht-api-production.up.railway.app/api` |
| `INTERNAL_API_KEY` | même clé que le backend |

### 5.5 Configurer BotFather

1. Ouvrir @BotFather → `/mybots` → choisir ton bot
2. Bot Settings → Domain → ajouter :
   ```
   scannerht-api-production.up.railway.app
   ```

---

## Phase 6 — Vérifications finales

### Checklist locale

- [ ] `python3 run_backend.py` démarre sans erreur
- [ ] `http://127.0.0.1:8000/api/health` retourne `{"status": "ok"}`
- [ ] `node bot/index.js` affiche "ScannerHT bot is running"
- [ ] `/start` dans Telegram affiche l'écran d'intro
- [ ] L'onboarding complet fonctionne (langue → coins → menu)
- [ ] Bouton Market affiche les données (ou erreur propre si backend down)

### Checklist Railway

- [ ] Backend déployé avec URL publique
- [ ] Volume monté sur `/data`
- [ ] `/api/health` accessible sur l'URL publique
- [ ] Bot déployé en service séparé
- [ ] `/start` fonctionne via Telegram sur le bot en production
- [ ] `HEALTH_DETAILS_ENABLED=false` (ne pas exposer les chemins en prod)

---

## Ordre de démarrage

```
1. Backend d'abord     → python3 run_backend.py
2. Vérifier le health  → curl http://127.0.0.1:8000/api/health
3. Bot ensuite         → node bot/index.js
4. Tester Telegram     → /start dans le chat du bot
```

> Le bot DÉPEND du backend. Toujours démarrer le backend en premier.
