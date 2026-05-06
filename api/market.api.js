const { apiRequest } = require("./client");

async function getMarketOverview(userId) {
  return apiRequest(`/users/${userId}/market`);
}

module.exports = {
  getMarketOverview,
};
