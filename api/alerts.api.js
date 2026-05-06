const { apiRequest } = require("./client");

async function getAlertsOverview(userId) {
  return apiRequest(`/users/${userId}/alerts`);
}

async function getAlertDeliveryJobs() {
  return apiRequest("/internal/alerts/jobs");
}

async function acknowledgeAlertDelivery(userId, digestKey) {
  return apiRequest(`/internal/alerts/${userId}/ack`, {
    method: "POST",
    body: JSON.stringify({
      digest_key: digestKey,
    }),
  });
}

module.exports = {
  getAlertsOverview,
  getAlertDeliveryJobs,
  acknowledgeAlertDelivery,
};
