const { apiRequest } = require("./client");

function toApiPatch(user) {
  return {
    intro_seen: Boolean(user.intro_seen),
    language: user.language ?? null,
    level: user.level ?? null,
    scanner_limit: user.scanner_limit ?? null,
    market: user.market ?? null,
    trading_style: user.trading_style ?? null,
    coins: Array.isArray(user.coins) ? user.coins : [],
    alerts_enabled: Boolean(user.alerts_enabled),
    alerts_min_priority: user.alerts_min_priority ?? "high",
    active_message_id: user.active_message_id ?? null,
  };
}

async function getUser(userId) {
  return apiRequest(`/users/${userId}`);
}

async function saveUser(user) {
  return apiRequest(`/users/${user.user_id}`, {
    method: "PATCH",
    body: JSON.stringify(toApiPatch(user)),
  });
}

module.exports = {
  getUser,
  saveUser,
  toApiPatch,
};
