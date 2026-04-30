# 🔧 FIXES — ScannerHT

Journal des corrections appliquées au projet.

---

## [2026-04-26] — Corrections v1

### 🔴 BUG CRITIQUE — `deleteActiveMessage` logique inversée
**Fichier :** `bot/index.js`
**Ligne :** ~2006

**Avant :** La condition `if (!message.includes("not found")) { return; }` avalait silencieusement toutes les erreurs SAUF "not found".
**Après :** Les erreurs inattendues sont loguées via `console.warn()` pour faciliter le debug.

---

### 🔴 BUG CRITIQUE — Handlers sans `try/catch`
**Fichier :** `bot/index.js`
**Handlers :** `bot.start`, `bot.command("reset")`, `bot.on("message")`

**Avant :** Une erreur réseau sur `getUser()` / `saveUser()` provoquait un spinner infini chez l'utilisateur Telegram.
**Après :** Chaque handler est wrappé dans `try/catch` avec un message d'erreur utilisateur et un log console.

---

### 🟡 AMÉLIORATION — Timeout sur les appels `fetch`
**Fichier :** `bot/index.js`
**Fonction :** `apiRequest()`

**Avant :** Aucune limite de temps sur les requêtes HTTP vers le backend. Un backend lent pouvait bloquer indéfiniment.
**Après :** `AbortController` avec timeout configurable (`API_FETCH_TIMEOUT_MS`, défaut : 10 000 ms).
**Variable d'env ajoutée :** `API_FETCH_TIMEOUT_MS` (optionnelle, défaut 10000)

---

### 🟡 AMÉLIORATION — `hmac.new()` avec `digestmod=` nommé
**Fichier :** `backend/auth.py`
**Lignes :** 23, 37, 122

**Avant :** `hmac.new(key, msg, hashlib.sha256)` — argument positionnel, déprécié dans les futures versions Python.
**Après :** `hmac.new(key, msg, digestmod=hashlib.sha256)` — forme canonique recommandée.

---

### 🟡 BUG POTENTIEL — `UserState.next_step` sans valeur par défaut
**Fichier :** `backend/schemas.py`
**Ligne :** 184

**Avant :** `next_step: str` — champ requis. Si le service oubliait de l'injecter, Pydantic levait une `ValidationError`.
**Après :** `next_step: str = ""` — valeur par défaut vide, compatible avec tous les retours existants.

---

### 🟡 SÉCURITÉ — Avertissement `WEB_SESSION_SECRET` fallback
**Fichier :** `backend/config.py`

**Avant :** Si `WEB_SESSION_SECRET` n'était pas dans `.env`, il prenait silencieusement la valeur de `BOT_TOKEN`.
**Après :** Un `warnings.warn()` est émis au démarrage pour alerter le développeur.

---

### 🟢 MAINTENABILITÉ — `require` explicite dans `app.js`
**Fichier :** `app.js`

**Avant :** `require("./bot")` — résolution implicite vers `bot/index.js`.
**Après :** `require("./bot/index.js")` — chemin explicite, sans ambiguïté.

---

### 🟢 CLARTÉ — Commentaire sur `TELEGRAM_MESSAGE_SAFE_LIMIT`
**Fichier :** `bot/index.js`

Ajout d'un commentaire expliquant pourquoi la limite est 3800 et non 4096 (marge pour emojis/encodage UTF-8).

---

## ⚠️ Points restants (non corrigés automatiquement)

| Point | Raison |
|-------|--------|
| `db.js` non utilisé | À supprimer manuellement après vérification qu'aucun script externe ne l'importe |
| Code dupliqué `renderXxxOverview` | Refactoring plus large, risque de régression — à faire dans une PR dédiée |

---

## 📋 Variable d'environnement ajoutée

```env
# Timeout (ms) pour les appels HTTP vers le backend FastAPI (défaut : 10000)
API_FETCH_TIMEOUT_MS=10000
```

Ajouter dans `.env` si tu veux personnaliser la valeur.
