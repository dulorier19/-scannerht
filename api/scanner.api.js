const { apiRequest } = require("./client");

async function getScannerOverview(userId) {
  return apiRequest(`/users/${userId}/scanner`);
}

module.exports = {
  getScannerOverview,
};
