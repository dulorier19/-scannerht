const fs = require("fs");
const path = require("path");
const Database = require("better-sqlite3");

const DATA_DIR = path.join(__dirname, "data");
const DB_FILE = path.join(DATA_DIR, "scannerht.sqlite");
const LEGACY_JSON_FILE = path.join(DATA_DIR, "users.json");

function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
}

ensureDataDir();

const db = new Database(DB_FILE);
db.pragma("journal_mode = WAL");

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    intro_seen INTEGER NOT NULL DEFAULT 0,
    language TEXT,
    market TEXT,
    trading_style TEXT,
    coins TEXT NOT NULL DEFAULT '[]',
    onboarding_complete INTEGER NOT NULL DEFAULT 0,
    active_message_id INTEGER
  )
`);

const userColumns = db.prepare("PRAGMA table_info(users)").all();
const hasIntroSeenColumn = userColumns.some((column) => column.name === "intro_seen");

if (!hasIntroSeenColumn) {
  db.exec("ALTER TABLE users ADD COLUMN intro_seen INTEGER NOT NULL DEFAULT 0");
}

const selectUserStatement = db.prepare(`
  SELECT user_id, intro_seen, language, market, trading_style, coins, onboarding_complete, active_message_id
  FROM users
  WHERE user_id = ?
`);

const upsertUserStatement = db.prepare(`
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
    @user_id,
    @intro_seen,
    @language,
    @market,
    @trading_style,
    @coins,
    @onboarding_complete,
    @active_message_id
  )
  ON CONFLICT(user_id) DO UPDATE SET
    intro_seen = excluded.intro_seen,
    language = excluded.language,
    market = excluded.market,
    trading_style = excluded.trading_style,
    coins = excluded.coins,
    onboarding_complete = excluded.onboarding_complete,
    active_message_id = excluded.active_message_id
`);

const countUsersStatement = db.prepare("SELECT COUNT(*) AS count FROM users");

function parseCoins(rawCoins) {
  if (!rawCoins) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawCoins);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    return [];
  }
}

function getDefaultUser(userId) {
  return {
    user_id: userId,
    intro_seen: false,
    language: null,
    market: null,
    trading_style: null,
    coins: [],
    onboarding_complete: false,
    active_message_id: null,
  };
}

function mapRowToUser(row) {
  if (!row) {
    return null;
  }

  return {
    user_id: row.user_id,
    intro_seen: Boolean(row.intro_seen),
    language: row.language || null,
    market: row.market || null,
    trading_style: row.trading_style || null,
    coins: parseCoins(row.coins),
    onboarding_complete: Boolean(row.onboarding_complete),
    active_message_id: row.active_message_id ?? null,
  };
}

function serializeUser(user) {
  return {
    user_id: user.user_id,
    intro_seen: user.intro_seen ? 1 : 0,
    language: user.language || null,
    market: user.market || null,
    trading_style: user.trading_style || null,
    coins: JSON.stringify(Array.isArray(user.coins) ? user.coins : []),
    onboarding_complete: user.onboarding_complete ? 1 : 0,
    active_message_id: user.active_message_id ?? null,
  };
}

function migrateLegacyUsers() {
  if (!fs.existsSync(LEGACY_JSON_FILE)) {
    return;
  }

  const { count } = countUsersStatement.get();

  if (count > 0) {
    return;
  }

  try {
    const raw = fs.readFileSync(LEGACY_JSON_FILE, "utf8");
    const users = raw.trim() ? JSON.parse(raw) : {};
    const records = Object.values(users).filter(Boolean);

    const insertMany = db.transaction((items) => {
      for (const item of items) {
        const fallbackId = Number(item.user_id);

        if (!Number.isInteger(fallbackId)) {
          continue;
        }

        upsertUserStatement.run(
          serializeUser({
            ...getDefaultUser(fallbackId),
            ...item,
            user_id: fallbackId,
          }),
        );
      }
    });

    insertMany(records);
  } catch (error) {
    return;
  }
}

migrateLegacyUsers();

function getUser(userId) {
  const row = selectUserStatement.get(userId);
  return mapRowToUser(row) || getDefaultUser(userId);
}

function saveUser(user) {
  upsertUserStatement.run(serializeUser(user));
}

module.exports = {
  DB_FILE,
  getDefaultUser,
  getUser,
  saveUser,
};
