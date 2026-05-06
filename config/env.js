require("dotenv").config();

function toNumber(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function minNumber(value, fallback, min) {
  return Math.max(min, toNumber(value, fallback));
}

const env = {
  nodeEnv: process.env.NODE_ENV || "development",
  botToken: process.env.BOT_TOKEN,
  apiBaseUrl: process.env.API_BASE_URL || "http://127.0.0.1:8000/api",
  internalApiKey: process.env.INTERNAL_API_KEY,
  welcomeImageUrl: process.env.WELCOME_IMAGE_URL,
  welcomeVideoUrl: process.env.WELCOME_VIDEO_URL,
  alertPollingIntervalMs: minNumber(process.env.ALERT_POLLING_INTERVAL_MS, 300_000, 30_000),
  telegramMessageSafeLimit: 3800,
  apiFetchTimeoutMs: toNumber(process.env.API_FETCH_TIMEOUT_MS, 10_000),
  port: toNumber(process.env.PORT, 0),
};

function assertRequiredEnv() {
  if (!env.botToken) {
    throw new Error("BOT_TOKEN is missing. Add it to your environment before starting the bot.");
  }
}

module.exports = {
  env,
  assertRequiredEnv,
};
