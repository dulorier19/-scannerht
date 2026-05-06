const COINS = [
  { symbol: "BTC", icon: "₿" },
  { symbol: "ETH", icon: "⟠" },
  { symbol: "SOL", icon: "◎" },
  { symbol: "DOGE", icon: "🐶" },
  { symbol: "AVAX", icon: "🔺" },
  { symbol: "MATIC", icon: "🟢" },
  { symbol: "LINK", icon: "🔷" },
  { symbol: "DOT", icon: "⚫" },
];

const TRADINGVIEW_SYMBOL_MAP = {
  BTC: "COINBASE-BTCUSD",
  ETH: "COINBASE-ETHUSD",
  SOL: "COINBASE-SOLUSD",
  DOGE: "COINBASE-DOGEUSD",
  AVAX: "COINBASE-AVAXUSD",
  MATIC: "COINBASE-POLUSD",
  LINK: "COINBASE-LINKUSD",
  DOT: "COINBASE-DOTUSD",
};

module.exports = {
  COINS,
  TRADINGVIEW_SYMBOL_MAP,
};
