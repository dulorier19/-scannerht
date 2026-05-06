const { apiRequest } = require("./client");

async function getSignalsOverview(userId) {
  return apiRequest(`/users/${userId}/signals`);
}

module.exports = {
  getSignalsOverview,
};
