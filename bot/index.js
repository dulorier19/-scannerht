require("dotenv").config();
const http = require("http");
const { Telegraf, Markup } = require("telegraf");

const BOT_TOKEN = process.env.BOT_TOKEN;
const API_BASE_URL = process.env.API_BASE_URL || "http://127.0.0.1:8000/api";
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY;
const WELCOME_IMAGE_URL = process.env.WELCOME_IMAGE_URL;
const WELCOME_VIDEO_URL = process.env.WELCOME_VIDEO_URL;
const ALERT_POLLING_INTERVAL_MS = Math.max(30_000, Number(process.env.ALERT_POLLING_INTERVAL_MS || 300_000));
// Limite sécurisée en dessous du max Telegram (4096 chars) pour laisser une marge aux emojis/encodage
const TELEGRAM_MESSAGE_SAFE_LIMIT = 3800;
const API_FETCH_TIMEOUT_MS = Number(process.env.API_FETCH_TIMEOUT_MS || 10_000);
const PORT = Number(process.env.PORT || 0);

if (!BOT_TOKEN) {
  throw new Error("BOT_TOKEN is missing. Add it to your environment before starting the bot.");
}

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

function getDefaultUser(userId) {
  return {
    user_id: userId,
    intro_seen: false,
    language: null,
    level: null,
    scanner_limit: null,
    market: null,
    trading_style: null,
    coins: [],
    alerts_enabled: false,
    alerts_min_priority: "high",
    onboarding_complete: false,
    active_message_id: null,
  };
}

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

async function apiRequest(path, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_FETCH_TIMEOUT_MS);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(INTERNAL_API_KEY ? { "X-Internal-API-Key": INTERNAL_API_KEY } : {}),
        ...(options.headers || {}),
      },
    });
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API request failed (${response.status}): ${errorBody}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
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

async function getMarketOverview(userId) {
  return apiRequest(`/users/${userId}/market`);
}

async function getSignalsOverview(userId) {
  return apiRequest(`/users/${userId}/signals`);
}

async function getAlertsOverview(userId) {
  return apiRequest(`/users/${userId}/alerts`);
}

async function getScannerOverview(userId) {
  return apiRequest(`/users/${userId}/scanner`);
}

async function getAlertDeliveryJobs() {
  return apiRequest("/internal/alerts/jobs");
}

async function acknowledgeAlertDelivery(userId, digestKey) {
  return apiRequest(`/internal/alerts/${userId}/ack`, {
    method: "POST",
    body: JSON.stringify({ digest_key: digestKey }),
  });
}

async function getTradeManagementJobs() {
  return apiRequest("/internal/trades/jobs");
}

async function acknowledgeTradeManagementEvent(userId, eventKey) {
  return apiRequest(`/internal/trades/${userId}/ack`, {
    method: "POST",
    body: JSON.stringify({ event_key: eventKey }),
  });
}

function getTradeManagementUi(language) {
  if (language === "fr") {
    return {
      simulationOnly: "Simulation uniquement • aucun ordre reel",
      tradeId: "Trade",
      price: "Prix",
      types: {
        tp1_hit: "TP1",
        tp2_hit: "TP2",
        tpf_hit: "TP final",
        sl_moved: "SL deplace",
        stopped: "Stop touche",
        invalidated: "Invalide",
      },
    };
  }

  if (language === "es") {
    return {
      simulationOnly: "Solo simulacion • ninguna orden real",
      tradeId: "Trade",
      price: "Precio",
      types: {
        tp1_hit: "TP1",
        tp2_hit: "TP2",
        tpf_hit: "TP final",
        sl_moved: "SL movido",
        stopped: "Stop alcanzado",
        invalidated: "Invalidado",
      },
    };
  }

  return {
    simulationOnly: "Simulation only • no real order",
    tradeId: "Trade",
    price: "Price",
    types: {
      tp1_hit: "TP1",
      tp2_hit: "TP2",
      tpf_hit: "Final TP",
      sl_moved: "SL moved",
      stopped: "Stopped",
      invalidated: "Invalidated",
    },
  };
}

function formatTradeManagementTelegramMessage(job) {
  const ui = getTradeManagementUi(job.language);
  const typeLabel = ui.types[job.event_type] || job.event_type;
  const lines = [];
  const message = typeof job.message === "string" ? job.message.trim() : "";
  const match = message.match(/^([A-Z0-9_-]+)\s+([A-Z]+):/);
  const symbol = (job.symbol || match?.[1] || "").trim();
  const direction = (match?.[2] || "").trim();
  const headlineParts = [`📌 ${typeLabel}`];

  if (symbol) {
    headlineParts.push(symbol);
  }
  if (direction) {
    headlineParts.push(direction);
  }
  lines.push(headlineParts.join(" | "));

  if (job.trade_id) {
    lines.push(`${ui.tradeId}: #${String(job.trade_id).slice(0, 8)}`);
  }

  if (typeof job.current_price === "number" && Number.isFinite(job.current_price) && job.current_price > 0) {
    lines.push(`${ui.price}: ${job.current_price.toFixed(2)}`);
  }

  if (message) {
    lines.push("");
    lines.push(message);
  }

  lines.push("");
  lines.push(ui.simulationOnly);
  return lines.join("\n");
}

const translations = {
  fr: {
    locale: "fr",
    introCaption:
      "🤖 ScannerHT\n\nLe cockpit crypto nouvelle generation.\n\nAnalyse rapide, scanner automatique et signaux dans une experience simple.",
    languagePrompt: "🌍\nChoose your language\nChoisis ta langue\nElige tu idioma",
    levelMessage: "Configuration 1/5\n\nQuel est ton niveau ?",
    marketMessage: "Configuration 2/5\n\nBienvenue 👋\n\nChoisis ton marché",
    styleMessage: "Configuration 3/5\n\nQuel est ton style de trading ?",
    coinsTitle: "Configuration 4/5\n\nChoisis 3 cryptos à suivre",
    settingsLanguageMessage: "⚙ Reglages\n\nChoisis ta langue",
    settingsLevelMessage: "⚙ Reglages\n\nChoisis ton niveau",
    settingsMarketMessage: "⚙ Reglages\n\nChoisis ton marché",
    settingsStyleMessage: "⚙ Reglages\n\nChoisis ton style de trading",
    settingsCoinsMessage: "⚙ Reglages\n\nChoisis exactement 3 cryptos à suivre",
    settingsScannerLimitMessage: "⚙ Reglages\n\nChoisis combien de cryptos le Scanner peut afficher",
    selectionLabel: "Sélection",
    selectedLabel: "Choisies",
    buttons: {
      spot: "📊 Spot",
      futures: "⚡ Futures",
      scalping: "⚡ Scalping",
      intraday: "📈 Intraday",
      market: "📊 Marche",
      signals: "🎯 Signaux",
      scanner: "📡 Scanner",
      alerts: "🚨 Alertes",
      settings: "⚙ Reglages",
      help: "❓ Aide",
      language: "🌍 Langue",
      level: "🎓 Niveau",
      scannerLimit: "📡 Scanner",
      marketPref: "📊 Marché",
      stylePref: "📈 Style",
      coinsPref: "🪙 Cryptos",
      restart: "🔄 Recommencer",
      back: "🔙 Retour",
      begin: "🚀 Commencer",
      marketBack: "🔙 Menu",
    },
    values: {
      language: {
        fr: "Français",
        en: "English",
        es: "Español",
      },
      level: {
        beginner: "Débutant",
        medium: "Moyen",
        pro: "Pro",
      },
      market: {
        spot: "Spot",
        futures: "Futures",
      },
      style: {
        scalping: "Scalping",
        intraday: "Intraday",
      },
      unset: "Non défini",
    },
    menuFeedback: {
      market: "Analyse du marché bientôt disponible.",
      signals: "Les signaux de trading arrivent bientôt.",
      scanner: "Le scanner automatique arrive bientôt.",
      alerts: "Les alertes de prix arrivent bientôt.",
      settings: "Le panneau de configuration arrive bientôt.",
      help: "L'aide utilisateur sera disponible ici.",
    },
    maxCoins: "Tu peux suivre exactement 3 cryptos.",
    alertsStatus: {
      on: "Armees",
      off: "Coupees",
      cooldown: "Attente",
    },
    alertsPriority: {
      title: "Priorite minimum",
      high: "Haute",
      medium: "Moyenne",
      low: "Basse",
    },
    alertsButtons: {
      arm: "🔔 Armer",
      disarm: "🔕 Pause",
      high: "Haute",
      medium: "Moyenne",
      low: "Basse",
      refresh: "↻ Actualiser",
    },
    alertsDeliveryLabel: "Livraison",
    alertsMeta: {
      lastSent: "Dernier envoi",
      nextWindow: "Prochaine fenetre",
      reason: "Motif",
      digestChanged: "digest modifie",
      urgentProximity: "proximite urgente",
      ready: "prete",
    },
    scannerMeta: {
      summary: "Resume",
      hot: "Chaud",
      building: "En construction",
      early: "Tot",
      score: "Score",
      urgency: "Urgence",
      invalidation: "Invalidation",
      alerts: "Alertes",
      armed: "armees",
      off: "coupees",
      selected: "liste suivie",
      discovery: "decouverte",
      playbook: "Plan de jeu",
    },
    common: {
      profile: "Profil",
      role: "Rôle",
      question: "Question",
      brief: "En bref",
      whatMatters: "Ce qui compte",
      doNow: "Action",
      focus: "Focus",
      watchNext: "À surveiller",
      source: "Source",
      updated: "Mis à jour",
      topSetup: "Setup principal",
      topQueue: "Priorité",
      topTrigger: "Declencheur principal",
      summary: "Résumé",
      execution: "Exécution",
      risk: "Risque",
      delivery: "Livraison",
      watchlist: "À surveiller",
      setups: "Configurations",
      queue: "File de surveillance",
      triggers: "Triggers",
      checklist: "Plan de jeu",
      none: "Aucun",
      never: "Jamais",
      regime: "Regime",
      status: "Statut",
      trigger: "Declencheur",
      action: "Action",
      conviction: "Conviction",
      price: "Prix",
      distance: "Distance",
      size: "Taille",
      thesis: "Hypothèse",
      catalyst: "Catalyseur",
      chart: "Graphique",
      chartOpen: "Ouvrir le graphique",
      entry: "Entree",
      mode: "Mode",
      sentiment: "Sentiment",
      volatility: "Volatilite",
      confidence: "Confiance",
      unavailable: "indisponible",
      cached: "cache",
      stale: "retard",
      autoMode: "auto",
      pulse: "Pulse",
      breakout: "Cassure",
    },
    desks: {
      market: {
        title: "📊 Marche | Contexte",
        role: "Lire l'environnement avant de prendre du risque.",
        question: "Le marché aide-t-il ou complique-t-il mes décisions ?",
      },
      signals: {
        title: "🎯 Signaux | Decision",
        role: "Choisir ce qui mérite une action maintenant.",
        question: "Quel setup mérite vraiment une entrée ?",
      },
      alerts: {
        title: "🚨 Alertes | Rappel",
        role: "Ramener ton attention seulement quand c'est utile.",
        question: "Quand dois-tu revenir sur le marché ?",
      },
      scanner: {
        title: "📡 Scanner | Surveillance",
        role: "Classer ce qu'il faut surveiller ensuite.",
        question: "Quelle idée monte dans la file d'attention ?",
      },
    },
    ui: {
      controlRoom: "Centre de commande",
      currentProfile: "Profil actuel",
      tracking: "Suivi",
      modeChanges: "Ce qui change avec le niveau",
      helpTitle: "Aide ScannerHT",
      howToUse: "Comment utiliser les ecrans",
      yourMode: "Ton mode",
      bestHabit: "Bonne habitude",
      chartZone: "Graphique",
      modeBeginner: "Debutant = moins de bruit, une action claire",
      modeMedium: "Medium = execution guidee",
      modePro: "Pro = plus de controle et plus de detail",
      flowMarket: "Marche = lire le contexte",
      flowSignals: "Signaux = decider maintenant",
      flowScanner: "Scanner = surveiller ensuite",
      flowAlerts: "Alertes = revenir au bon moment",
      useMarket: "Commence par Marche pour lire le contexte.",
      useSignals: "Ouvre Signaux pour trouver le setup le plus propre maintenant.",
      useScanner: "Utilise Scanner pour classer ce qui merite l'attention ensuite.",
      useAlerts: "Arme les Alertes pour que le marche revienne a toi.",
      habit: "Contexte puis decision puis scan puis alertes.",
    },
    feedback: {
      alertsPriorityLocked: "La priorite suit deja ton niveau.",
    },
  },
  en: {
    locale: "en",
    introCaption:
      "🤖 ScannerHT\n\nThe next-gen crypto cockpit.\n\nFast analysis, auto scanner and trading signals in one clean experience.",
    languagePrompt: "🌍\nChoose your language\nChoisis ta langue\nElige tu idioma",
    levelMessage: "Setup 1/5\n\nWhat is your level?",
    marketMessage: "Setup 2/5\n\nWelcome 👋\n\nChoose your market",
    styleMessage: "Setup 3/5\n\nWhat is your trading style?",
    coinsTitle: "Setup 4/5\n\nChoose 3 cryptos to track",
    settingsLanguageMessage: "⚙ Settings\n\nChoose your language",
    settingsLevelMessage: "⚙ Settings\n\nChoose your level",
    settingsMarketMessage: "⚙ Settings\n\nChoose your market",
    settingsStyleMessage: "⚙ Settings\n\nChoose your trading style",
    settingsCoinsMessage: "⚙ Settings\n\nChoose exactly 3 cryptos to track",
    settingsScannerLimitMessage: "⚙ Settings\n\nChoose how many cryptos Scanner can show",
    selectionLabel: "Selection",
    selectedLabel: "Selected",
    buttons: {
      spot: "📊 Spot",
      futures: "⚡ Futures",
      scalping: "⚡ Scalping",
      intraday: "📈 Intraday",
      market: "📊 Market",
      signals: "🎯 Signals",
      scanner: "📡 Scanner",
      alerts: "🚨 Alerts",
      settings: "⚙ Settings",
      help: "❓ Help",
      language: "🌍 Language",
      level: "🎓 Level",
      scannerLimit: "📡 Scanner",
      marketPref: "📊 Market",
      stylePref: "📈 Style",
      coinsPref: "🪙 Coins",
      restart: "🔄 Restart",
      back: "🔙 Back",
      begin: "🚀 Start",
      marketBack: "🔙 Menu",
    },
    values: {
      language: {
        fr: "Français",
        en: "English",
        es: "Español",
      },
      level: {
        beginner: "Beginner",
        medium: "Medium",
        pro: "Pro",
      },
      market: {
        spot: "Spot",
        futures: "Futures",
      },
      style: {
        scalping: "Scalping",
        intraday: "Intradia",
      },
      unset: "Not set",
    },
    menuFeedback: {
      market: "Market analysis will be available soon.",
      signals: "Trading signals are coming soon.",
      scanner: "Auto scanner is coming soon.",
      alerts: "Price alerts are coming soon.",
      settings: "Settings panel is coming soon.",
      help: "User help will be available here.",
    },
    maxCoins: "You can track exactly 3 cryptos.",
    alertsStatus: {
      on: "Armed",
      off: "Off",
      cooldown: "Cooldown",
    },
    alertsPriority: {
      title: "Minimum priority",
      high: "High",
      medium: "Medium",
      low: "Low",
    },
    alertsButtons: {
      arm: "🔔 Arm",
      disarm: "🔕 Pause",
      high: "High",
      medium: "Medium",
      low: "Low",
      refresh: "↻ Refresh",
    },
    alertsDeliveryLabel: "Delivery",
    alertsMeta: {
      lastSent: "Last sent",
      nextWindow: "Next window",
      reason: "Reason",
      digestChanged: "digest changed",
      urgentProximity: "urgent proximity",
      ready: "ready",
    },
    scannerMeta: {
      summary: "Summary",
      hot: "Hot",
      building: "Building",
      early: "Early",
      score: "Score",
      urgency: "Urgency",
      invalidation: "Invalidation",
      alerts: "Alerts",
      armed: "armed",
      off: "off",
      selected: "watchlist",
      discovery: "discovery",
      playbook: "Playbook",
    },
    common: {
      profile: "Profile",
      role: "Role",
      question: "Question",
      brief: "In short",
      whatMatters: "What matters",
      doNow: "Do now",
      focus: "Focus",
      watchNext: "Watch next",
      source: "Source",
      updated: "Updated",
      topSetup: "Top setup",
      topQueue: "Top queue",
      topTrigger: "Top trigger",
      summary: "Summary",
      execution: "Execution",
      risk: "Risk",
      delivery: "Delivery",
      watchlist: "Watchlist",
      setups: "Setups",
      queue: "Queue",
      triggers: "Triggers",
      checklist: "Playbook",
      none: "None",
      never: "Never",
      regime: "Regime",
      status: "Status",
      trigger: "Trigger",
      action: "Action",
      conviction: "Conviction",
      price: "Price",
      distance: "Distance",
      size: "Size",
      thesis: "Thesis",
      catalyst: "Catalyst",
      chart: "Chart",
      chartOpen: "Open chart",
      entry: "Entry",
      mode: "Mode",
      sentiment: "Sentiment",
      volatility: "Volatility",
      confidence: "Confidence",
      unavailable: "n/a",
      cached: "cached",
      stale: "stale",
      autoMode: "auto",
      pulse: "Pulse",
      breakout: "Breakout",
    },
    desks: {
      market: {
        title: "📊 Market | Context",
        role: "Read the environment before taking risk.",
        question: "Is the market helping or fighting your decisions?",
      },
      signals: {
        title: "🎯 Signals | Decision",
        role: "Choose what deserves action right now.",
        question: "Which setup is worth an entry now?",
      },
      alerts: {
        title: "🚨 Alerts | Return",
        role: "Bring your attention back only when it matters.",
        question: "When should you come back to the market?",
      },
      scanner: {
        title: "📡 Scanner | Watch next",
        role: "Rank what deserves attention next.",
        question: "Which idea is moving up the queue?",
      },
    },
    ui: {
      controlRoom: "Control room",
      currentProfile: "Current profile",
      tracking: "Tracking",
      modeChanges: "What changes with your level",
      helpTitle: "ScannerHT Help",
      howToUse: "How to use the screens",
      yourMode: "Your mode",
      bestHabit: "Best habit",
      chartZone: "Chart",
      modeBeginner: "Beginner = less noise, one clear action",
      modeMedium: "Medium = guided execution",
      modePro: "Pro = more control and more detail",
      flowMarket: "Market = read the context",
      flowSignals: "Signals = decide now",
      flowScanner: "Scanner = watch next",
      flowAlerts: "Alerts = come back at the right moment",
      useMarket: "Start with Market to read the context.",
      useSignals: "Open Signals to find the cleanest setup now.",
      useScanner: "Use Scanner to rank what deserves attention next.",
      useAlerts: "Arm Alerts so the market comes back to you.",
      habit: "Context, then decision, then scanner, then alerts.",
    },
    feedback: {
      alertsPriorityLocked: "Priority is already fixed by your level.",
    },
  },
  es: {
    locale: "es",
    introCaption:
      "🤖 ScannerHT\n\nTu cockpit cripto de nueva generacion.\n\nAnalisis rapido, scanner automatico y senales en una experiencia simple.",
    languagePrompt: "🌍\nChoose your language\nChoisis ta langue\nElige tu idioma",
    levelMessage: "Configuracion 1/5\n\nCual es tu nivel?",
    marketMessage: "Configuracion 2/5\n\nBienvenido 👋\n\nElige tu mercado",
    styleMessage: "Configuracion 3/5\n\nCual es tu estilo de trading?",
    coinsTitle: "Configuracion 4/5\n\nElige 3 criptos para seguir",
    settingsLanguageMessage: "⚙ Ajustes\n\nElige tu idioma",
    settingsLevelMessage: "⚙ Ajustes\n\nElige tu nivel",
    settingsMarketMessage: "⚙ Ajustes\n\nElige tu mercado",
    settingsStyleMessage: "⚙ Ajustes\n\nElige tu estilo de trading",
    settingsCoinsMessage: "⚙ Ajustes\n\nElige exactamente 3 criptos para seguir",
    settingsScannerLimitMessage: "⚙ Ajustes\n\nElige cuantas criptos puede mostrar el Scanner",
    selectionLabel: "Seleccion",
    selectedLabel: "Elegidas",
    buttons: {
      spot: "📊 Spot",
      futures: "⚡ Futuros",
      scalping: "⚡ Scalping",
      intraday: "📈 Intradia",
      market: "📊 Mercado",
      signals: "🎯 Senales",
      scanner: "📡 Scanner",
      alerts: "🚨 Alertas",
      settings: "⚙ Ajustes",
      help: "❓ Ayuda",
      language: "🌍 Idioma",
      level: "🎓 Nivel",
      scannerLimit: "📡 Scanner",
      marketPref: "📊 Mercado",
      stylePref: "📈 Estilo",
      coinsPref: "🪙 Criptos",
      restart: "🔄 Reiniciar",
      back: "🔙 Volver",
      begin: "🚀 Empezar",
      marketBack: "🔙 Menu",
    },
    values: {
      language: {
        fr: "Français",
        en: "English",
        es: "Español",
      },
      level: {
        beginner: "Principiante",
        medium: "Medio",
        pro: "Pro",
      },
      market: {
        spot: "Spot",
        futures: "Futuros",
      },
      style: {
        scalping: "Scalping",
        intraday: "Intradia",
      },
      unset: "No definido",
    },
    menuFeedback: {
      market: "El analisis de mercado estara disponible pronto.",
      signals: "Las senales de trading llegaran pronto.",
      scanner: "El scanner automatico llegara pronto.",
      alerts: "Las alertas de precio llegaran pronto.",
      settings: "El panel de configuracion llegara pronto.",
      help: "La ayuda estara disponible aqui.",
    },
    maxCoins: "Puedes seguir exactamente 3 criptos.",
    alertsStatus: {
      on: "Activadas",
      off: "Pausadas",
      cooldown: "Espera",
    },
    alertsPriority: {
      title: "Prioridad minima",
      high: "Alta",
      medium: "Media",
      low: "Baja",
    },
    alertsButtons: {
      arm: "🔔 Activar",
      disarm: "🔕 Pausar",
      high: "Alta",
      medium: "Media",
      low: "Baja",
      refresh: "↻ Refrescar",
    },
    alertsDeliveryLabel: "Entrega",
    alertsMeta: {
      lastSent: "Ultimo envio",
      nextWindow: "Proxima ventana",
      reason: "Motivo",
      digestChanged: "digest cambiado",
      urgentProximity: "proximidad urgente",
      ready: "lista",
    },
    scannerMeta: {
      summary: "Resumen",
      hot: "Caliente",
      building: "Construyendo",
      early: "Temprano",
      score: "Score",
      urgency: "Urgencia",
      invalidation: "Invalidacion",
      alerts: "Alertas",
      armed: "activas",
      off: "pausadas",
      selected: "lista seguida",
      discovery: "descubrimiento",
      playbook: "Plan",
    },
    common: {
      profile: "Perfil",
      role: "Rol",
      question: "Pregunta",
      brief: "En breve",
      whatMatters: "Lo importante",
      doNow: "Accion",
      focus: "Foco",
      watchNext: "Vigilar",
      source: "Fuente",
      updated: "Actualizado",
      topSetup: "Setup principal",
      topQueue: "Prioridad",
      topTrigger: "Disparador principal",
      summary: "Resumen",
      execution: "Ejecucion",
      risk: "Riesgo",
      delivery: "Entrega",
      watchlist: "Seguimiento",
      setups: "Setups",
      queue: "Cola",
      triggers: "Triggers",
      checklist: "Plan",
      none: "Ninguno",
      never: "Nunca",
      regime: "Regimen",
      status: "Estado",
      trigger: "Disparador",
      action: "Accion",
      conviction: "Conviccion",
      price: "Precio",
      distance: "Distancia",
      size: "Tamano",
      thesis: "Tesis",
      catalyst: "Catalizador",
      chart: "Grafico",
      chartOpen: "Abrir grafico",
      entry: "Entrada",
      mode: "Modo",
      sentiment: "Sentimiento",
      volatility: "Volatilidad",
      confidence: "Confianza",
      unavailable: "n/d",
      cached: "cache",
      stale: "retrasado",
      autoMode: "auto",
      pulse: "Pulso",
      breakout: "Ruptura",
    },
    desks: {
      market: {
        title: "📊 Mercado | Contexto",
        role: "Leer el entorno antes de tomar riesgo.",
        question: "El mercado ayuda o complica tus decisiones?",
      },
      signals: {
        title: "🎯 Senales | Decision",
        role: "Elegir lo que merece accion ahora.",
        question: "Que setup merece una entrada ahora?",
      },
      alerts: {
        title: "🚨 Alertas | Regreso",
        role: "Traer tu atencion solo cuando valga la pena.",
        question: "Cuando deberias volver al mercado?",
      },
      scanner: {
        title: "📡 Scanner | Vigilancia",
        role: "Ordenar lo que merece atencion despues.",
        question: "Que idea sube en la cola de seguimiento?",
      },
    },
    ui: {
      controlRoom: "Centro de control",
      currentProfile: "Perfil actual",
      tracking: "Seguimiento",
      modeChanges: "Lo que cambia con el nivel",
      helpTitle: "Ayuda ScannerHT",
      howToUse: "Como usar las pantallas",
      yourMode: "Tu modo",
      bestHabit: "Mejor habito",
      chartZone: "Grafico",
      modeBeginner: "Principiante = menos ruido, una accion clara",
      modeMedium: "Medio = ejecucion guiada",
      modePro: "Pro = mas control y mas detalle",
      flowMarket: "Mercado = leer el contexto",
      flowSignals: "Senales = decidir ahora",
      flowScanner: "Scanner = vigilar despues",
      flowAlerts: "Alertas = volver en el momento correcto",
      useMarket: "Empieza por Mercado para leer el contexto.",
      useSignals: "Abre Senales para ver el setup mas claro ahora.",
      useScanner: "Usa Scanner para ordenar lo que merece atencion despues.",
      useAlerts: "Activa Alertas para que el mercado vuelva a ti.",
      habit: "Contexto, luego decision, luego scanner, luego alertas.",
    },
    feedback: {
      alertsPriorityLocked: "La prioridad ya la fija tu nivel.",
    },
  },
};

function getCopy(language) {
  return translations[language] || translations.en;
}

function refreshCompletion(user) {
  user.onboarding_complete = Boolean(
    user.language &&
      user.level &&
      user.market &&
      user.trading_style &&
      Array.isArray(user.coins) &&
      user.coins.length === 3,
  );
}

function getNextStep(user) {
  if (!user.intro_seen) {
    return "intro";
  }

  if (!user.language) {
    return "language";
  }

  if (!user.level) {
    return "level";
  }

  if (!user.market) {
    return "market";
  }

  if (!user.trading_style) {
    return "style";
  }

  if (!Array.isArray(user.coins) || user.coins.length !== 3) {
    return "coins";
  }

  return "welcome";
}

function coinLabel(coin, selected) {
  return `${selected ? "✅ " : ""}${coin.icon} ${coin.symbol}`;
}

function formatValue(group, key, copy) {
  if (!key) {
    return copy.values.unset;
  }

  return copy.values[group][key] || copy.values.unset;
}

function formatCoinsValue(user, copy) {
  return Array.isArray(user.coins) && user.coins.length ? user.coins.join(", ") : copy.values.unset;
}

function replaceTokens(template, values) {
  return Object.entries(values).reduce((output, [key, value]) => {
    return output.replaceAll(`{${key}}`, value);
  }, template);
}

function buildCoinKeyboard(actionPrefix, selectedCoins, showBackButton, backCallback, copy) {
  const rows = [];

  for (let index = 0; index < COINS.length; index += 2) {
    const pair = COINS.slice(index, index + 2).map((coin) =>
      Markup.button.callback(
        coinLabel(coin, selectedCoins.includes(coin.symbol)),
        `${actionPrefix}:${coin.symbol}`,
      ),
    );
    rows.push(pair);
  }

  if (showBackButton) {
    rows.push([Markup.button.callback(copy.buttons.back, backCallback)]);
  }

  return rows;
}

function formatMarketProvider(provider) {
  if (!provider) {
    return null;
  }

  if (provider === "coingecko") {
    return "CoinGecko";
  }

  if (provider === "coinbase") {
    return "Coinbase";
  }

  if (provider === "binance") {
    return "Binance";
  }

  return provider;
}

const LOCALIZED_TERMS = {
  fr: {
    statuses: {
      Active: "Actif",
      Watch: "Surveillance",
      "Stand aside": "Attente",
      Hot: "Chaud",
      Building: "Construction",
      Early: "Tot",
      Immediate: "Immediate",
      Near: "Proche",
      Monitor: "Surveiller",
      High: "Haute",
      Medium: "Moyenne",
      Low: "Basse",
      "High conviction": "Conviction forte",
      "Building conviction": "Conviction en construction",
      "Low conviction": "Conviction faible",
    },
    replacements: [
      ["Trend continuation", "Tendance de continuation"],
      ["Breakout watch", "Surveillance de cassure"],
      ["Range / reset", "Range / reinitialisation"],
      ["Fast momentum", "Momentum rapide"],
      ["Session range", "Range de session"],
      ["Long bias", "Biais haussier"],
      ["Watch for reclaim", "Surveiller la reprise"],
      ["Long continuation", "Continuation haussiere"],
      ["Momentum reclaim", "Reprise de momentum"],
      ["Reclaim watch", "Surveillance de reprise"],
      ["No edge yet", "Pas d'avantage clair"],
      ["Continuation confirm", "Confirmation de continuation"],
      ["Bullish confirmation", "Confirmation haussiere"],
      ["Reclaim trigger", "Declenchement de reprise"],
      ["Recovery trigger", "Declenchement de reprise"],
      ["Standby recovery", "Reprise de secours"],
      ["Price is close to a valid continuation trigger. Stay ready for confirmation.", "Le prix se rapproche d'un declenchement valide de continuation. Reste pret pour la confirmation."],
      ["Structure is improving, but it still needs a reclaim before risk makes sense.", "La structure s'ameliore, mais il faut encore une reprise avant d'engager du risque."],
      ["No clean edge yet. Only a stronger recovery should bring this back into focus.", "Pas d'avantage propre pour l'instant. Seule une reprise plus nette doit remettre cette idee au premier plan."],
      ["Several setups are aligned. Focus on the cleanest continuation instead of forcing all of them.", "Plusieurs setups sont alignes. Concentre-toi sur la continuation la plus propre au lieu de tout forcer."],
      ["One setup stands out. Let the rest confirm before spreading attention too wide.", "Un setup se detache. Laisse le reste confirmer avant de trop disperser ton attention."],
      ["Watchlist is forming, but confirmation still matters more than anticipation.", "La watchlist se construit, mais la confirmation compte encore plus que l'anticipation."],
      ["No strong signal right now. Capital preservation is the active decision.", "Pas de signal fort pour l'instant. La preservation du capital reste la vraie decision."],
      ["Several alert candidates are close. Let alerts bring the market to you instead of camping on the chart.", "Plusieurs alertes se rapprochent. Laisse les alertes ramener le marche a toi au lieu de rester colle au chart."],
      ["One alert stands out as the clearest near-term trigger.", "Une alerte ressort comme le trigger le plus clair a court terme."],
      ["The watchlist is constructive, but most moves still need confirmation.", "La watchlist est constructive, mais la plupart des mouvements demandent encore une confirmation."],
      ["Nothing needs urgent attention right now. Alerts should protect focus, not create noise.", "Rien ne demande une attention urgente pour l'instant. Les alertes doivent proteger le focus, pas creer du bruit."],
      ["Scanner sees multiple names close to execution. Focus the first pass on the hottest trigger, not the whole list.", "Le Scanner voit plusieurs noms proches de l'execution. Concentre le premier passage sur le trigger le plus chaud, pas sur toute la liste."],
      ["One scanner candidate stands above the rest right now.", "Un candidat Scanner se detache du reste pour l'instant."],
      ["Scanner is finding constructive structures, but most still need proof before they deserve full attention.", "Le Scanner trouve des structures constructives, mais la plupart ont encore besoin de preuve avant de meriter toute ton attention."],
      ["Scanner is quiet enough to protect your focus. No need to force activity while structure is still early.", "Le Scanner est assez calme pour proteger ton focus. Inutile de forcer l'activite tant que la structure reste precoce."],
      ["Start with Hot names and let Building names wait their turn.", "Commence par les noms chauds et laisse les noms en construction attendre leur tour."],
      ["If the trigger is not clean, keep the idea in Scanner instead of forcing a trade.", "Si le trigger n'est pas propre, laisse l'idee dans le Scanner au lieu de forcer un trade."],
      ["Use alerts to protect attention and re-check the chart only when Scanner gets closer.", "Utilise les alertes pour proteger ton attention et ne reviens sur le chart que lorsque le Scanner se rapproche."],
      ["Alert on breakout confirmation, then execute only if follow-through holds.", "Alerte sur confirmation de cassure, puis execute seulement si le mouvement tient."],
      ["Let the alert bring the pair back to you instead of front-running the move.", "Laisse l'alerte ramener la paire a toi au lieu d'anticiper le mouvement."],
      ["Keep it on alerts only and skip active risk until the structure resets.", "Garde cette idee en alertes seulement et evite le risque actif tant que la structure ne se remet pas en place."],
      ["High velocity. Cut size and avoid chasing extension candles.", "Vitesse elevee. Reduis la taille et evite de chasser les bougies d'extension."],
      ["Moderate volatility. Wait for confirmation before committing full size.", "Volatilite moderee. Attends la confirmation avant de prendre la taille complete."],
      ["Controlled conditions. Favor clean structure over speed.", "Conditions controlees. Favorise une structure propre plutot que la vitesse."],
      ["Downgraded because the broader tape is defensive. Wait for stronger confirmation.", "Abaisse car le contexte global est defensif. Attends une confirmation plus forte."],
      ["Downgraded because the broader tape is defensive and the reclaim is still weak.", "Abaisse car le contexte global est defensif et la reprise reste faible."],
      ["Downgraded because volatility is still too fast for a clean first entry.", "Abaisse car la volatilite est encore trop rapide pour une premiere entree propre."],
      ["Downgraded because volatility is too unstable for a reclaim setup right now.", "Abaisse car la volatilite est trop instable pour une reprise propre maintenant."],
      ["Start with reduced size and add only after a clean confirmation.", "Commence avec une taille reduite et ajoute seulement apres une confirmation propre."],
      ["Start normal size only after confirmation. Add only if follow-through holds.", "Commence avec une taille normale seulement apres confirmation. Ajoute seulement si le mouvement tient."],
      ["Use starter size only if the trigger confirms. Avoid full size on anticipation.", "Utilise une petite taille seulement si le trigger confirme. Evite la taille complete sur anticipation."],
      ["Use ", "Utilise "],
      ["Prioritize ", "Priorise "],
      [" first, then check trigger, size, and invalidation before entry.", " en premier, puis verifie le declencheur, la taille et l'invalidation avant l'entree."],
      [" first and keep the others as secondary ideas.", " en premier et garde les autres comme idees secondaires."],
      ["No size. Keep it on alerts only until structure improves.", "Pas de taille. Garde cette idee en alertes seulement jusqu'a amelioration de la structure."],
      ["Act only if price holds above ", "Agis seulement si le prix tient au-dessus de "],
      ["Trigger only on a reclaim through ", "Declenche seulement sur reprise au-dessus de "],
      ["Stand aside until price reclaims ", "Reste a l'ecart jusqu'a reprise au-dessus de "],
      ["Abort if price loses ", "Abandonne si le prix repasse sous "],
      ["Stay flat if price keeps closing below ", "Reste a plat si le prix continue de cloturer sous "],
      ["Skip it until structure repairs above ", "Ignore cette idee tant que la structure ne se repare pas au-dessus de "],
      ["Stand down if price slips back under ", "Abandonne si le prix repasse sous "],
      [" after confirmation.", " apres confirmation."],
      [" with follow-through.", " avec continuite."],
      [" and the reclaim never sticks.", " et que la reprise ne tient pas."],
      [" with momentum.", " avec impulsion."],
      [" after the confirmation instead of holding above it.", " apres la confirmation au lieu de tenir au-dessus."],
      [" after the trigger instead of holding above it.", " apres le trigger au lieu de tenir au-dessus."],
      [" and momentum fades.", " et que le momentum s'affaiblit."],
      [" around ", " vers "],
    ],
  },
  es: {
    statuses: {
      Active: "Activo",
      Watch: "Vigilancia",
      "Stand aside": "Espera",
      Hot: "Caliente",
      Building: "Construyendo",
      Early: "Temprano",
      Immediate: "Inmediato",
      Near: "Cerca",
      Monitor: "Vigilar",
      High: "Alta",
      Medium: "Media",
      Low: "Baja",
      "High conviction": "Conviccion alta",
      "Building conviction": "Conviccion en construccion",
      "Low conviction": "Conviccion baja",
    },
    replacements: [
      ["Trend continuation", "Continuacion de tendencia"],
      ["Breakout watch", "Vigilancia de ruptura"],
      ["Range / reset", "Rango / reinicio"],
      ["Fast momentum", "Momentum rapido"],
      ["Session range", "Rango de sesion"],
      ["Long bias", "Sesgo alcista"],
      ["Watch for reclaim", "Vigilar recuperacion"],
      ["Long continuation", "Continuacion alcista"],
      ["Momentum reclaim", "Recuperacion de momentum"],
      ["Reclaim watch", "Vigilancia de recuperacion"],
      ["No edge yet", "Sin ventaja clara"],
      ["Continuation confirm", "Confirmacion de continuacion"],
      ["Bullish confirmation", "Confirmacion alcista"],
      ["Reclaim trigger", "Trigger de recuperacion"],
      ["Recovery trigger", "Trigger de recuperacion"],
      ["Standby recovery", "Recuperacion en espera"],
      ["Price is close to a valid continuation trigger. Stay ready for confirmation.", "El precio esta cerca de un trigger valido de continuacion. Mantente listo para la confirmacion."],
      ["Structure is active, but trigger quality still needs a cleaner confirmation.", "La estructura esta activa, pero la calidad del disparador todavia necesita una confirmacion mas limpia."],
      ["Structure is improving, but it still needs a reclaim before risk makes sense.", "La estructura mejora, pero aun necesita una recuperacion antes de asumir riesgo."],
      ["No clean edge yet. Only a stronger recovery should bring this back into focus.", "Aun no hay ventaja limpia. Solo una recuperacion mas fuerte debe devolver esta idea al foco."],
      ["Several setups are aligned. Focus on the cleanest continuation instead of forcing all of them.", "Varios setups estan alineados. Enfocate en la continuacion mas limpia en lugar de forzarlo todo."],
      ["One setup stands out. Let the rest confirm before spreading attention too wide.", "Un setup destaca. Deja que el resto confirme antes de dispersar demasiado tu atencion."],
      ["Watchlist is forming, but confirmation still matters more than anticipation.", "La watchlist se esta formando, pero la confirmacion sigue siendo mas importante que la anticipacion."],
      ["No strong signal right now. Capital preservation is the active decision.", "No hay una senal fuerte ahora. Preservar capital sigue siendo la decision activa."],
      ["Several alert candidates are close. Let alerts bring the market to you instead of camping on the chart.", "Varias alertas estan cerca. Deja que las alertas traigan el mercado a ti en lugar de quedarte pegado al grafico."],
      ["One alert stands out as the clearest near-term trigger.", "Una alerta destaca como el trigger mas claro a corto plazo."],
      ["The watchlist is constructive, but most moves still need confirmation.", "La watchlist es constructiva, pero la mayoria de movimientos aun necesita confirmacion."],
      ["Nothing needs urgent attention right now. Alerts should protect focus, not create noise.", "Nada necesita atencion urgente ahora. Las alertas deben proteger el foco, no crear ruido."],
      ["Scanner sees multiple names close to execution. Focus the first pass on the hottest trigger, not the whole list.", "El Scanner ve varios nombres cerca de ejecucion. Enfoca la primera pasada en el trigger mas caliente, no en toda la lista."],
      ["One scanner candidate stands above the rest right now.", "Un candidato del Scanner destaca sobre el resto ahora mismo."],
      ["Scanner is finding constructive structures, but most still need proof before they deserve full attention.", "El Scanner encuentra estructuras constructivas, pero la mayoria aun necesita prueba antes de merecer toda tu atencion."],
      ["Scanner is quiet enough to protect your focus. No need to force activity while structure is still early.", "El Scanner esta lo bastante tranquilo para proteger tu foco. No hace falta forzar actividad mientras la estructura siga temprana."],
      ["Start with Hot names and let Building names wait their turn.", "Empieza por los nombres calientes y deja que los que se construyen esperen su turno."],
      ["If the trigger is not clean, keep the idea in Scanner instead of forcing a trade.", "Si el trigger no es limpio, deja la idea en Scanner en lugar de forzar un trade."],
      ["Use alerts to protect attention and re-check the chart only when Scanner gets closer.", "Usa alertas para proteger la atencion y revisa el grafico solo cuando el Scanner se acerque."],
      ["Alert on breakout confirmation, then execute only if follow-through holds.", "Alerta en confirmacion de ruptura y ejecuta solo si el movimiento se sostiene."],
      ["Let the alert bring the pair back to you instead of front-running the move.", "Deja que la alerta devuelva el par a tu pantalla en lugar de anticipar el movimiento."],
      ["Keep it on alerts only and skip active risk until the structure resets.", "Dejalo solo en alertas y evita riesgo activo hasta que la estructura se reinicie."],
      ["High velocity. Cut size and avoid chasing extension candles.", "Velocidad alta. Reduce tamano y evita perseguir velas de extension."],
      ["Moderate volatility. Wait for confirmation before committing full size.", "Volatilidad moderada. Espera confirmacion antes de usar tamano completo."],
      ["Controlled conditions. Favor clean structure over speed.", "Condiciones controladas. Prioriza estructura limpia sobre velocidad."],
      ["Downgraded because the broader tape is defensive. Wait for stronger confirmation.", "Bajado porque el contexto general es defensivo. Espera una confirmacion mas fuerte."],
      ["Downgraded because the broader tape is defensive and the reclaim is still weak.", "Bajado porque el contexto general es defensivo y la recuperacion sigue debil."],
      ["Downgraded because volatility is still too fast for a clean first entry.", "Bajado porque la volatilidad sigue demasiado rapida para una primera entrada limpia."],
      ["Downgraded because volatility is too unstable for a reclaim setup right now.", "Bajado porque la volatilidad es demasiado inestable para una recuperacion limpia ahora."],
      ["Start with reduced size and add only after a clean confirmation.", "Empieza con tamano reducido y agrega solo despues de una confirmacion limpia."],
      ["Start normal size only after confirmation. Add only if follow-through holds.", "Empieza con tamano normal solo despues de la confirmacion. Agrega solo si el movimiento se sostiene."],
      ["Use starter size only if the trigger confirms. Avoid full size on anticipation.", "Usa tamano inicial solo si el trigger confirma. Evita tamano completo por anticipacion."],
      ["No size. Keep it on alerts only until structure improves.", "Sin tamano. Mantenlo solo en alertas hasta que la estructura mejore."],
      ["Act only if price holds above ", "Actua solo si el precio se mantiene por encima de "],
      ["Trigger only on a reclaim through ", "Activa solo en recuperacion por encima de "],
      ["Stand aside until price reclaims ", "Mantente al margen hasta que el precio recupere "],
      ["Abort if price loses ", "Cancela si el precio pierde "],
      ["Stay flat if price keeps closing below ", "Mantente fuera si el precio sigue cerrando por debajo de "],
      ["Skip it until structure repairs above ", "Ignoralo hasta que la estructura se repare por encima de "],
      ["Stand down if price slips back under ", "Abandona si el precio vuelve por debajo de "],
      [" after confirmation.", " despues de la confirmacion."],
      [" with follow-through.", " con continuidad."],
      [" and the reclaim never sticks.", " y la recuperacion nunca se sostiene."],
      [" with momentum.", " con impulso."],
      [" after the confirmation instead of holding above it.", " despues de la confirmacion en lugar de sostenerse arriba."],
      [" after the trigger instead of holding above it.", " despues del trigger en lugar de sostenerse arriba."],
      [" and momentum fades.", " y el impulso se apaga."],
      ["watchlist", "lista de seguimiento"],
      ["trigger", "disparador"],
      ["Cooldown", "Enfriamiento"],
      ["digests", "resumenes"],
      [" around ", " cerca de "],
    ],
  },
};

function formatMarketUpdatedAt(value) {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed.toISOString().replace(".000Z", " UTC").replace("T", " ");
}

function localizeTerm(copy, value) {
  const locale = copy.locale;
  if (!locale || !LOCALIZED_TERMS[locale]) {
    return value;
  }
  return LOCALIZED_TERMS[locale].statuses[value] || value;
}

function localizeText(copy, value) {
  if (!value) {
    return value;
  }
  const locale = copy.locale;
  if (!locale || !LOCALIZED_TERMS[locale]) {
    return value;
  }

  return LOCALIZED_TERMS[locale].replacements.reduce((output, [from, to]) => output.split(from).join(to), value);
}

function buildTradingViewLink(symbol) {
  const mapped = TRADINGVIEW_SYMBOL_MAP[symbol] || TRADINGVIEW_SYMBOL_MAP.BTC;
  return `https://www.tradingview.com/symbols/${mapped}/`;
}

function formatAlertsDeliveryStatus(copy, value) {
  if (value === "cooldown") {
    return copy.alertsStatus.cooldown;
  }
  if (value === "armed") {
    return copy.alertsStatus.on;
  }
  return copy.alertsStatus.off;
}

function formatAlertsDeliveryReason(copy, value) {
  if (value === "urgent-proximity") {
    return copy.alertsMeta.urgentProximity;
  }
  if (value === "digest-changed") {
    return copy.alertsMeta.digestChanged;
  }
  return copy.alertsMeta.ready;
}

function getUserLevel(value) {
  const level = typeof value === "string" ? value : value?.level;
  if (level === "beginner" || level === "medium" || level === "pro") {
    return level;
  }
  return "medium";
}

function getEffectiveScannerLimit(user) {
  const level = getUserLevel(user);
  if (level === "beginner") {
    return 3;
  }
  if (level === "medium") {
    return 5;
  }

  const configured = Number(user?.scanner_limit);
  if (Number.isInteger(configured)) {
    return Math.max(3, Math.min(configured, COINS.length));
  }
  return COINS.length;
}

function syncScannerLimitByLevel(user, forceDefault = false) {
  const level = getUserLevel(user);
  if (level === "beginner") {
    user.scanner_limit = 3;
    return;
  }
  if (level === "medium") {
    user.scanner_limit = 5;
    return;
  }

  if (forceDefault || !Number.isInteger(user.scanner_limit)) {
    user.scanner_limit = COINS.length;
  }
}

function formatScannerLimitValue(user) {
  const level = getUserLevel(user);
  const effective = getEffectiveScannerLimit(user);
  const copy = getCopy(user?.language);
  if (level === "beginner" || level === "medium") {
    return `${effective} ${copy.common.autoMode}`;
  }
  return `${effective} ${user?.language === "fr" ? "cryptos" : user?.language === "es" ? "criptos" : "coins"}`;
}

function getEffectiveAlertsPriority(user) {
  const level = getUserLevel(user);
  if (level === "beginner") {
    return "high";
  }
  if (level === "medium") {
    return "medium";
  }
  return user?.alerts_min_priority || "high";
}

function getDeskItemLimit(level) {
  if (level === "beginner") {
    return 1;
  }
  if (level === "medium") {
    return 3;
  }
  return 99;
}

function formatCompactPrice(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }

  return `$${Number(value).toFixed(value >= 1 ? 2 : 6)}`;
}

function formatCompactPercent(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }

  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatCompactDistance(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }

  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function buildSourceLines(copy, overview) {
  const marketProvider = formatMarketProvider(overview.data_provider);
  const marketUpdatedAt = formatMarketUpdatedAt(overview.data_updated_at);
  return [
    marketProvider
      ? `${copy.common.source}: ${marketProvider}${overview.data_cached ? ` (${copy.common.cached})` : ""}${overview.data_stale ? ` (${copy.common.stale})` : ""}`
      : null,
    marketUpdatedAt ? `${copy.common.updated}: ${marketUpdatedAt}` : null,
  ].filter(Boolean);
}

function buildSection(title, lines) {
  const items = (lines || []).filter(Boolean);
  if (!items.length) {
    return null;
  }
  return [`◆ ${title}`, ...items.map((line) => (line.startsWith("• ") ? line : `• ${line}`))].join("\n");
}

function joinMessageBlocks(blocks) {
  return blocks.filter(Boolean).join("\n\n");
}

function trimTelegramText(text, limit = TELEGRAM_MESSAGE_SAFE_LIMIT) {
  if (!text || text.length <= limit) {
    return text;
  }

  const suffix = "\n\n…";
  return `${text.slice(0, Math.max(0, limit - suffix.length)).trimEnd()}${suffix}`;
}

function buildFittedMessage(baseBlocks, listTitle, items, tailBlocks, emptyValue) {
  const normalizedItems = items && items.length ? items : [emptyValue];
  let visibleItems = [];

  for (const item of normalizedItems) {
    const candidateItems = [...visibleItems, item];
    const candidateText = joinMessageBlocks([
      ...baseBlocks,
      buildSection(listTitle, candidateItems),
      ...tailBlocks,
    ]);

    if (candidateText.length > TELEGRAM_MESSAGE_SAFE_LIMIT) {
      break;
    }

    visibleItems = candidateItems;
  }

  if (!visibleItems.length) {
    visibleItems = [normalizedItems[0]];
  }

  return trimTelegramText(
    joinMessageBlocks([
      ...baseBlocks,
      buildSection(listTitle, visibleItems),
      ...tailBlocks,
    ]),
  );
}

function buildTitleBlock(title, subtitle) {
  return subtitle ? `${title}\n◦ ${subtitle}` : title;
}

function buildProfileSnapshot(copy, user) {
  return [
    `${copy.common.profile}: ${formatValue("level", user?.level, copy)}`,
    `${copy.buttons.scanner}: ${formatScannerLimitValue(user)}`,
    `${copy.buttons.marketPref}: ${formatValue("market", user?.market, copy)}`,
    `${copy.buttons.stylePref}: ${formatValue("style", user?.trading_style, copy)}`,
  ];
}

function buildWelcomeText(copy, user) {
  return joinMessageBlocks([
    buildTitleBlock("🤖 ScannerHT", copy.ui.controlRoom),
    buildSection(copy.ui.controlRoom, [
      copy.ui.flowMarket,
      copy.ui.flowSignals,
      copy.ui.flowScanner,
      copy.ui.flowAlerts,
    ]),
    buildSection(copy.ui.currentProfile, [
      `${copy.common.profile}: ${formatValue("level", user?.level, copy)}`,
      `${copy.buttons.scanner}: ${formatScannerLimitValue(user)}`,
      `${copy.buttons.coinsPref}: ${formatCoinsValue(user, copy)}`,
    ]),
  ]);
}

function buildHelpText(copy, user) {
  const level = getUserLevel(user);
  const alertsPriority = getEffectiveAlertsPriority(user);
  return joinMessageBlocks([
    buildTitleBlock(`❓ ${copy.ui.helpTitle}`, copy.ui.habit),
    buildSection(copy.ui.howToUse, [
      copy.ui.useMarket,
      copy.ui.useSignals,
      copy.ui.useScanner,
      copy.ui.useAlerts,
    ]),
    buildSection(copy.ui.yourMode, [
      `${copy.common.profile}: ${formatValue("level", level, copy)}`,
      `${copy.buttons.scanner}: ${formatScannerLimitValue(user)}`,
      `${copy.alertsPriority.title}: ${localizeTerm(copy, alertsPriority[0].toUpperCase() + alertsPriority.slice(1))}`,
    ]),
    buildSection(copy.ui.bestHabit, [
      copy.ui.habit,
    ]),
  ]);
}

function buildSettingsHomeText(copy, user) {
  return joinMessageBlocks([
    buildTitleBlock(`⚙ ${copy.buttons.settings.replace("⚙ ", "")}`, copy.ui.currentProfile),
    buildSection(copy.ui.currentProfile, buildProfileSnapshot(copy, user)),
    buildSection(copy.ui.tracking, [
      `${copy.buttons.coinsPref}: ${formatCoinsValue(user, copy)}`,
      `${copy.buttons.language}: ${formatValue("language", user?.language, copy)}`,
    ]),
    buildSection(copy.ui.modeChanges, [
      copy.ui.modeBeginner,
      copy.ui.modeMedium,
      copy.ui.modePro,
    ]),
  ]);
}

function buildDeskPrelude(copy, deskKey, overview, level) {
  const desk = copy.desks[deskKey];
  const lines = [desk.title, `${copy.common.profile}: ${formatValue("level", level, copy)}`];

  if (level === "beginner") {
    lines.push(`${copy.common.regime}: ${localizeText(copy, overview.regime)}`);
  } else if (level === "medium") {
    lines.push(`${copy.common.role}: ${desk.role}`, `${copy.common.regime}: ${localizeText(copy, overview.regime)}`);
  } else {
    lines.push(
      `${copy.common.role}: ${desk.role}`,
      `${copy.common.question}: ${desk.question}`,
      `${copy.common.regime}: ${localizeText(copy, overview.regime)}`,
    );
  }

  lines.push(...buildSourceLines(copy, overview));
  return buildTitleBlock(lines[0], lines.slice(1).join(" · "));
}

function buildMarketAssetLine(asset, level, copy) {
  const parts = [
    asset.symbol,
    formatCompactPrice(asset.last_price),
    formatCompactPercent(asset.price_change_percent),
    localizeText(copy, asset.bias),
  ];

  if (level === "pro") {
    parts.push(`${copy.common.pulse} ${asset.pulse_score}`, `${copy.common.breakout} ${asset.breakout_score}`);
  }

  return `• ${parts.filter(Boolean).join(" | ")}`;
}

function buildSignalLine(setup, level, copy) {
  const marketLine = [formatCompactPrice(setup.last_price), formatCompactPercent(setup.price_change_percent)].filter(Boolean).join(" | ");
  const status = localizeTerm(copy, setup.status);
  const conviction = localizeTerm(copy, setup.conviction);
  const direction = localizeText(copy, setup.direction);
  const trigger = localizeText(copy, setup.entry_trigger);
  const invalidation = localizeText(copy, setup.invalidation);
  const size = localizeText(copy, setup.size_plan);
  const entry = localizeText(copy, setup.entry_plan);
  const risk = localizeText(copy, setup.risk_note);
  const why = localizeText(copy, setup.why_this_signal);
  const confidenceExplanation = localizeText(copy, setup.confidence_explanation);
  const contextNote = localizeText(copy, setup.context_note);

  if (level === "beginner") {
    return `• ${setup.symbol}\n  ${copy.common.trigger}: ${trigger}\n  ${why}`;
  }

  if (level === "medium") {
    const firstLine = [setup.symbol, status, conviction, marketLine].filter(Boolean).join(" | ");
    return `• ${firstLine}\n  ${copy.common.action}: ${direction}\n  ${copy.common.trigger}: ${trigger}\n  ${copy.common.size}: ${size}\n  ${copy.common.thesis}: ${why}\n  ${copy.common.risk}: ${risk}\n  ${copy.scannerMeta.invalidation}: ${invalidation}`;
  }

  const proHeader = [setup.symbol, status, `${copy.common.confidence} ${setup.confidence}`, marketLine].filter(Boolean).join(" | ");
  return `• ${proHeader}\n  ${direction} | ${conviction} | ${setup.timeframe}\n  ${copy.common.trigger}: ${trigger}\n  ${copy.common.thesis}: ${why}\n  ${copy.common.confidence}: ${confidenceExplanation}\n  ${copy.common.entry}: ${entry}\n  ${copy.common.size}: ${size}\n  ${copy.common.focus}: ${contextNote}\n  ${copy.scannerMeta.invalidation}: ${invalidation}\n  ${copy.common.risk}: ${risk}`;
}

function buildAlertLine(item, level, copy) {
  const trigger = item.trigger_price ? formatCompactPrice(item.trigger_price) : copy.common.unavailable;
  const distance = formatCompactDistance(item.distance_percent);
  const priority = localizeTerm(copy, item.priority);
  const alertType = localizeText(copy, item.alert_type);
  const direction = localizeText(copy, item.direction);
  const action = localizeText(copy, item.action_note);
  const why = localizeText(copy, item.why_this_signal);
  const confidenceExplanation = localizeText(copy, item.confidence_explanation);
  const contextNote = localizeText(copy, item.context_note);
  const invalidation = localizeText(copy, item.invalidation);
  const risk = localizeText(copy, item.risk_note);
  const compactTrigger = `${copy.common.trigger}: ${trigger}${distance ? ` | ${copy.common.distance} ${distance}` : ""}`;
  const header = [item.symbol, priority].filter(Boolean).join(" | ");
  const shortAction = action || why || alertType || direction;

  if (level === "beginner") {
    return `• ${header}\n  ${compactTrigger}\n  ${copy.common.action}: ${shortAction}`;
  }

  if (level === "medium") {
    const mediumTail = invalidation || risk;
    return `• ${header}\n  ${compactTrigger}\n  ${copy.common.action}: ${shortAction}\n  ${mediumTail ? `${invalidation ? copy.scannerMeta.invalidation : copy.common.risk}: ${mediumTail}` : ""}`.replace(/\n\s*$/, "");
  }

  const proMeta = [alertType, direction, formatCompactPrice(item.last_price)].filter(Boolean).join(" | ");
  return `• ${header}\n  ${proMeta}\n  ${compactTrigger}\n  ${copy.common.action}: ${shortAction}\n  ${copy.common.confidence}: ${confidenceExplanation}\n  ${copy.common.focus}: ${contextNote}\n  ${copy.scannerMeta.invalidation}: ${invalidation}\n  ${copy.common.risk}: ${risk}`;
}

function buildScannerLine(candidate, level, copy) {
  const scopeLabel = candidate.watchlist_match ? copy.scannerMeta.selected : copy.scannerMeta.discovery;
  const status = localizeTerm(copy, candidate.status);
  const urgency = localizeTerm(copy, candidate.urgency);
  const pattern = localizeText(copy, candidate.pattern);
  const catalyst = localizeText(copy, candidate.catalyst);
  const triggerPlan = localizeText(copy, candidate.trigger_plan);
  const invalidation = localizeText(copy, candidate.invalidation);
  const why = localizeText(copy, candidate.why_this_signal);
  const confidenceExplanation = localizeText(copy, candidate.confidence_explanation);
  const contextNote = localizeText(copy, candidate.context_note);
  const risk = localizeText(copy, candidate.risk_note);
  const firstLine = [
    `#${candidate.rank}`,
    candidate.symbol,
    status,
    scopeLabel,
    formatCompactPrice(candidate.last_price),
    formatCompactPercent(candidate.price_change_percent),
  ]
    .filter(Boolean)
    .join(" | ");

  if (level === "beginner") {
    return `• ${candidate.symbol}\n  ${copy.common.trigger}: ${triggerPlan}\n  ${why}`;
  }

  if (level === "medium") {
    return `• ${firstLine}\n  ${copy.common.action}: ${pattern}\n  ${copy.common.trigger}: ${triggerPlan}\n  ${copy.common.thesis}: ${why}\n  ${copy.scannerMeta.urgency}: ${urgency}\n  ${copy.common.risk}: ${risk}`;
  }

  return `• ${firstLine}\n  ${pattern}\n  ${copy.scannerMeta.score}: ${candidate.scanner_score} | ${copy.scannerMeta.urgency}: ${urgency} | ${copy.scannerMeta.alerts}: ${candidate.alert_ready ? copy.scannerMeta.armed : copy.scannerMeta.off}\n  ${copy.common.trigger}: ${triggerPlan}\n  ${copy.common.catalyst}: ${catalyst}\n  ${copy.common.thesis}: ${why}\n  ${copy.common.confidence}: ${confidenceExplanation}\n  ${copy.common.focus}: ${contextNote}\n  ${copy.scannerMeta.invalidation}: ${invalidation}\n  ${copy.common.risk}: ${risk}`;
}

function buildMarketText(copy, marketOverview, levelValue) {
  const level = getUserLevel(levelValue);
  const assets = marketOverview.assets.slice(0, getDeskItemLimit(level)).map((asset) => buildMarketAssetLine(asset, level, copy));
  const topSymbol = marketOverview.assets[0]?.symbol || "BTC";

  if (level === "beginner") {
    return trimTelegramText(joinMessageBlocks([
      buildDeskPrelude(copy, "market", marketOverview, level),
      buildSection(copy.common.brief, [localizeText(copy, marketOverview.outlook_headline)]),
      buildSection(copy.common.doNow, [localizeText(copy, marketOverview.checklist[0])]),
      buildSection(copy.common.watchNext, [assets[0] || copy.common.none]),
      buildSection(copy.ui.chartZone, [`${topSymbol} · ${copy.common.chartOpen}: ${buildTradingViewLink(topSymbol)}`]),
    ]));
  }

  return trimTelegramText(joinMessageBlocks([
    buildDeskPrelude(copy, "market", marketOverview, level),
    buildSection(copy.common.whatMatters, [
      localizeText(copy, marketOverview.outlook_headline),
      `${copy.common.focus}: ${localizeText(copy, marketOverview.focus_window)}`,
      `${copy.common.summary}: ${copy.common.sentiment} ${marketOverview.sentiment_score}/100 | ${copy.common.volatility} ${localizeText(copy, marketOverview.volatility_label)}`,
    ]),
    buildSection(copy.common.doNow, [localizeText(copy, marketOverview.checklist[0])]),
    buildSection(copy.common.watchlist, assets),
    buildSection(copy.ui.chartZone, [`${topSymbol} · ${copy.common.chartOpen}: ${buildTradingViewLink(topSymbol)}`]),
    level === "pro" ? buildSection(copy.common.checklist, marketOverview.checklist.map((item) => localizeText(copy, item))) : null,
  ]));
}

function buildSignalsText(copy, signalsOverview, levelValue) {
  const level = getUserLevel(levelValue);
  const signalLimit = level === "beginner" ? 1 : level === "medium" ? 2 : 3;
  const setups = signalsOverview.setups.slice(0, signalLimit).map((setup) => buildSignalLine(setup, level, copy));
  const topSymbol = signalsOverview.top_symbol || signalsOverview.setups[0]?.symbol || "BTC";
  const topSetup = signalsOverview.setups[0];
  const setupsLabel = copy.common.setups;

  if (level === "beginner") {
    return trimTelegramText(joinMessageBlocks([
      buildDeskPrelude(copy, "signals", signalsOverview, level),
      buildSection(copy.common.brief, [
        topSetup ? `${copy.common.conviction}: ${localizeTerm(copy, topSetup.conviction)}` : null,
        localizeText(copy, signalsOverview.headline),
      ]),
      buildSection(copy.common.doNow, [localizeText(copy, signalsOverview.next_action)]),
      buildSection(setupsLabel, setups.length ? setups : [copy.common.none]),
      buildSection(copy.ui.chartZone, [`${topSymbol} · ${copy.common.chartOpen}: ${buildTradingViewLink(topSymbol)}`]),
    ]));
  }

  if (level === "medium") {
    return trimTelegramText(joinMessageBlocks([
      buildDeskPrelude(copy, "signals", signalsOverview, level),
      buildSection(copy.common.whatMatters, [
        localizeText(copy, signalsOverview.headline),
        topSetup ? `${copy.common.conviction}: ${localizeTerm(copy, topSetup.conviction)}` : null,
        `${copy.common.risk}: ${localizeText(copy, signalsOverview.risk_posture)}`,
      ]),
      buildSection(copy.common.doNow, [localizeText(copy, signalsOverview.next_action)]),
      buildSection(setupsLabel, setups.length ? setups : [copy.common.none]),
      buildSection(copy.ui.chartZone, [`${topSymbol} · ${copy.common.chartOpen}: ${buildTradingViewLink(topSymbol)}`]),
    ]));
  }

  return buildFittedMessage(
    [
      buildDeskPrelude(copy, "signals", signalsOverview, level),
      buildSection(copy.common.whatMatters, [
        localizeText(copy, signalsOverview.headline),
        `${copy.common.execution}: ${signalsOverview.ready_count} ${localizeTerm(copy, "Active")} / ${signalsOverview.watch_count} ${localizeTerm(copy, "Watch")} / ${signalsOverview.cool_off_count} ${localizeTerm(copy, "Stand aside")}`,
        `${copy.common.risk}: ${localizeText(copy, signalsOverview.risk_posture)}`,
      ]),
      buildSection(copy.common.doNow, [localizeText(copy, signalsOverview.next_action)]),
    ],
    setupsLabel,
    setups,
    [
      buildSection(copy.ui.chartZone, [`${topSymbol} · ${copy.common.chartOpen}: ${buildTradingViewLink(topSymbol)}`]),
      buildSection(copy.common.checklist, signalsOverview.checklist.map((item) => localizeText(copy, item))),
    ],
    copy.common.none,
  );
}

function buildAlertsText(copy, alertsOverview, levelValue) {
  const level = getUserLevel(levelValue);
  const alertLimit = level === "beginner" ? 1 : level === "medium" ? 2 : 3;
  const items = alertsOverview.items.slice(0, alertLimit).map((item) => buildAlertLine(item, level, copy));
  const topSymbol = alertsOverview.top_symbol || alertsOverview.items[0]?.symbol || "BTC";
  const topItem = alertsOverview.items[0];

  if (level === "beginner") {
    return trimTelegramText(joinMessageBlocks([
      buildDeskPrelude(copy, "alerts", alertsOverview, level),
      buildSection(copy.common.brief, [
        `${copy.alertsPriority.title}: ${localizeTerm(copy, alertsOverview.delivery_min_priority)}`,
        localizeText(copy, alertsOverview.headline),
      ]),
      buildSection(copy.common.doNow, [localizeText(copy, alertsOverview.next_action)]),
      buildSection(copy.common.triggers, items.length ? items : [copy.common.none]),
      buildSection(copy.ui.chartZone, [`${topSymbol} · ${copy.common.chartOpen}: ${buildTradingViewLink(topSymbol)}`]),
    ]));
  }

  if (level === "medium") {
    return trimTelegramText(joinMessageBlocks([
      buildDeskPrelude(copy, "alerts", alertsOverview, level),
      buildSection(copy.common.whatMatters, [
        localizeText(copy, alertsOverview.headline),
        topItem ? `${copy.alertsPriority.title}: ${localizeTerm(copy, topItem.priority)}` : null,
        topItem ? `${copy.common.trigger}: ${topItem.trigger_price ? formatCompactPrice(topItem.trigger_price) : copy.common.unavailable}` : null,
        topItem && typeof topItem.distance_percent === "number"
          ? `${copy.common.distance}: ${formatCompactDistance(topItem.distance_percent)}`
          : null,
      ]),
      buildSection(copy.common.doNow, [localizeText(copy, alertsOverview.next_action)]),
      buildSection(copy.common.triggers, items.length ? items : [copy.common.none]),
      buildSection(copy.ui.chartZone, [`${topSymbol} · ${copy.common.chartOpen}: ${buildTradingViewLink(topSymbol)}`]),
    ]));
  }

  return buildFittedMessage(
    [
      buildDeskPrelude(copy, "alerts", alertsOverview, level),
      buildSection(copy.common.whatMatters, [
        localizeText(copy, alertsOverview.headline),
        `${copy.common.summary}: ${alertsOverview.high_priority_count} ${localizeTerm(copy, "High")} / ${alertsOverview.medium_priority_count} ${localizeTerm(copy, "Medium")} / ${alertsOverview.low_priority_count} ${localizeTerm(copy, "Low")}`,
      ]),
      buildSection(copy.common.doNow, [localizeText(copy, alertsOverview.next_action)]),
      buildSection(copy.common.delivery, [
        localizeText(copy, alertsOverview.delivery_note),
        `${copy.common.status}: ${formatAlertsDeliveryStatus(copy, alertsOverview.delivery_status)}`,
        `${copy.alertsPriority.title}: ${localizeTerm(copy, alertsOverview.delivery_min_priority)}`,
        level === "pro"
          ? `${copy.alertsMeta.lastSent}: ${formatMarketUpdatedAt(alertsOverview.delivery_last_sent_at) || copy.common.never}`
          : null,
        level === "pro"
          ? `${copy.alertsMeta.nextWindow}: ${formatMarketUpdatedAt(alertsOverview.delivery_next_eligible_at) || copy.alertsMeta.ready}`
          : null,
        level === "pro" && alertsOverview.delivery_reason
          ? `${copy.alertsMeta.reason}: ${formatAlertsDeliveryReason(copy, alertsOverview.delivery_reason)}`
          : null,
      ]),
    ],
    copy.common.triggers,
    items,
    [buildSection(copy.ui.chartZone, [`${topSymbol} · ${copy.common.chartOpen}: ${buildTradingViewLink(topSymbol)}`])],
    copy.common.none,
  );
}

function buildScannerText(copy, scannerOverview, levelValue) {
  const level = getUserLevel(levelValue);
  const candidates = scannerOverview.candidates.map((candidate) => buildScannerLine(candidate, level, copy));
  const topSymbol = scannerOverview.top_symbol || scannerOverview.candidates[0]?.symbol || "BTC";

  if (level === "beginner") {
    return trimTelegramText(joinMessageBlocks([
      buildDeskPrelude(copy, "scanner", scannerOverview, level),
      buildSection(copy.common.brief, [
        `${copy.common.topQueue}: ${scannerOverview.top_symbol || copy.common.none}`,
        localizeText(copy, scannerOverview.headline),
      ]),
      buildSection(copy.common.doNow, [localizeText(copy, scannerOverview.next_action)]),
      buildSection(copy.common.queue, candidates.length ? candidates : [copy.common.none]),
      buildSection(copy.ui.chartZone, [`${topSymbol} · ${copy.common.chartOpen}: ${buildTradingViewLink(topSymbol)}`]),
    ]));
  }

  return buildFittedMessage(
    [
      buildDeskPrelude(copy, "scanner", scannerOverview, level),
      buildSection(copy.common.whatMatters, [
        `${copy.common.topQueue}: ${scannerOverview.top_symbol || copy.common.none}`,
        localizeText(copy, scannerOverview.headline),
        `${copy.common.summary}: ${scannerOverview.visible_count}/${scannerOverview.universe_size} | ${scannerOverview.hot_count} ${copy.scannerMeta.hot} / ${scannerOverview.building_count} ${copy.scannerMeta.building} / ${scannerOverview.early_count} ${copy.scannerMeta.early}`,
        `${copy.common.focus}: ${localizeText(copy, scannerOverview.scan_window)}`,
      ]),
      buildSection(copy.common.doNow, [localizeText(copy, scannerOverview.next_action)]),
    ],
    copy.common.queue,
    candidates,
    [
      buildSection(copy.ui.chartZone, [`${topSymbol} · ${copy.common.chartOpen}: ${buildTradingViewLink(topSymbol)}`]),
      level === "pro"
        ? buildSection(copy.scannerMeta.playbook, [
            localizeText(copy, "Start with Hot names and let Building names wait their turn."),
            localizeText(copy, "If the trigger is not clean, keep the idea in Scanner instead of forcing a trade."),
            localizeText(copy, "Use alerts to protect attention and re-check the chart only when Scanner gets closer."),
          ])
        : null,
    ],
    copy.common.none,
  );
}

function buildAlertsKeyboard(copy, user) {
  const currentPriority = getEffectiveAlertsPriority(user);
  const rows = [
    [
      Markup.button.callback(
        user.alerts_enabled ? copy.alertsButtons.disarm : copy.alertsButtons.arm,
        `alerts_toggle:${user.alerts_enabled ? "off" : "on"}`,
      ),
      Markup.button.callback(copy.alertsButtons.refresh, "menu:alerts"),
    ],
  ];

  if (getUserLevel(user) === "pro") {
    rows.push([
      Markup.button.callback(
        `${currentPriority === "high" ? "✅ " : ""}${copy.alertsButtons.high}`,
        "alerts_priority:high",
      ),
      Markup.button.callback(
        `${currentPriority === "medium" ? "✅ " : ""}${copy.alertsButtons.medium}`,
        "alerts_priority:medium",
      ),
      Markup.button.callback(
        `${currentPriority === "low" ? "✅ " : ""}${copy.alertsButtons.low}`,
        "alerts_priority:low",
      ),
    ]);
  }

  rows.push([Markup.button.callback(copy.buttons.marketBack, "alerts:back")]);
  return Markup.inlineKeyboard(rows);
}

function buildScreen(user, step) {
  const copy = getCopy(user.language);

  if (step === "intro") {
    const extra = Markup.inlineKeyboard([
      [Markup.button.callback(copy.buttons.begin, "intro:begin")],
    ]);

    if (WELCOME_VIDEO_URL) {
      return {
        kind: "video",
        media: WELCOME_VIDEO_URL,
        caption: copy.introCaption,
        extra,
      };
    }

    if (WELCOME_IMAGE_URL) {
      return {
        kind: "photo",
        media: WELCOME_IMAGE_URL,
        caption: copy.introCaption,
        extra,
      };
    }

    return {
      kind: "text",
      text: copy.introCaption,
      extra,
    };
  }

  if (step === "language") {
    return {
      kind: "text",
      text: copy.languagePrompt,
      extra: Markup.inlineKeyboard([
        [Markup.button.callback("🇫🇷 Français", "lang:fr")],
        [Markup.button.callback("🇺🇸 English", "lang:en")],
        [Markup.button.callback("🇪🇸 Español", "lang:es")],
      ]),
    };
  }

  if (step === "market") {
    return {
      kind: "text",
      text: copy.marketMessage,
      extra: Markup.inlineKeyboard([
        [
          Markup.button.callback(copy.buttons.spot, "market:spot"),
          Markup.button.callback(copy.buttons.futures, "market:futures"),
        ],
      ]),
    };
  }

  if (step === "style") {
    return {
      kind: "text",
      text: copy.styleMessage,
      extra: Markup.inlineKeyboard([
        [
          Markup.button.callback(copy.buttons.scalping, "style:scalping"),
          Markup.button.callback(copy.buttons.intraday, "style:intraday"),
        ],
      ]),
    };
  }

  if (step === "coins") {
    const coins = Array.isArray(user.coins) ? user.coins : [];
    const selectedLine = coins.length ? `\n${copy.selectedLabel}: ${coins.join(", ")}` : "";

    return {
      kind: "text",
      text: `${copy.coinsTitle}\n\n${copy.selectionLabel}: ${coins.length}/3${selectedLine}`,
      extra: Markup.inlineKeyboard(buildCoinKeyboard("coin", coins, false, "", copy)),
    };
  }

  if (step === "settings-home") {
    return {
      kind: "text",
      text: buildSettingsHomeText(copy, user),
      extra: Markup.inlineKeyboard([
        [
          Markup.button.callback(copy.buttons.language, "settings:language"),
          Markup.button.callback(copy.buttons.level, "settings:level"),
        ],
        user.level === "pro"
          ? [
              Markup.button.callback(copy.buttons.scannerLimit, "settings:scanner_limit"),
              Markup.button.callback(copy.buttons.marketPref, "settings:market"),
            ]
          : [
              Markup.button.callback(copy.buttons.marketPref, "settings:market"),
              Markup.button.callback(copy.buttons.stylePref, "settings:style"),
            ],
        user.level === "pro"
          ? [
              Markup.button.callback(copy.buttons.stylePref, "settings:style"),
              Markup.button.callback(copy.buttons.coinsPref, "settings:coins"),
            ]
          : [Markup.button.callback(copy.buttons.coinsPref, "settings:coins")],
        [
          Markup.button.callback(copy.buttons.restart, "settings:reset"),
          Markup.button.callback(copy.buttons.back, "settings:back"),
        ],
      ]),
    };
  }

  if (step === "level") {
    return {
      kind: "text",
      text: copy.levelMessage,
      extra: Markup.inlineKeyboard([
        [Markup.button.callback(`🌱 ${copy.values.level.beginner}`, "level:beginner")],
        [Markup.button.callback(`🧭 ${copy.values.level.medium}`, "level:medium")],
        [Markup.button.callback(`⚔️ ${copy.values.level.pro}`, "level:pro")],
      ]),
    };
  }

  if (step === "settings-language") {
    return {
      kind: "text",
      text: copy.settingsLanguageMessage,
      extra: Markup.inlineKeyboard([
        [Markup.button.callback("🇫🇷 Français", "settings_lang:fr")],
        [Markup.button.callback("🇺🇸 English", "settings_lang:en")],
        [Markup.button.callback("🇪🇸 Español", "settings_lang:es")],
        [Markup.button.callback(copy.buttons.back, "settings:home")],
      ]),
    };
  }

  if (step === "settings-level") {
    return {
      kind: "text",
      text: copy.settingsLevelMessage,
      extra: Markup.inlineKeyboard([
        [Markup.button.callback(`🌱 ${copy.values.level.beginner}`, "settings_level:beginner")],
        [Markup.button.callback(`🧭 ${copy.values.level.medium}`, "settings_level:medium")],
        [Markup.button.callback(`⚔️ ${copy.values.level.pro}`, "settings_level:pro")],
        [Markup.button.callback(copy.buttons.back, "settings:home")],
      ]),
    };
  }

  if (step === "settings-scanner-limit") {
    return {
      kind: "text",
      text: copy.settingsScannerLimitMessage,
      extra: Markup.inlineKeyboard([
        [
          Markup.button.callback("3", "settings_scanner_limit:3"),
          Markup.button.callback("4", "settings_scanner_limit:4"),
          Markup.button.callback("5", "settings_scanner_limit:5"),
        ],
        [
          Markup.button.callback("6", "settings_scanner_limit:6"),
          Markup.button.callback("7", "settings_scanner_limit:7"),
          Markup.button.callback("8", "settings_scanner_limit:8"),
        ],
        [Markup.button.callback(copy.buttons.back, "settings:home")],
      ]),
    };
  }

  if (step === "settings-market") {
    return {
      kind: "text",
      text: copy.settingsMarketMessage,
      extra: Markup.inlineKeyboard([
        [
          Markup.button.callback(copy.buttons.spot, "settings_market:spot"),
          Markup.button.callback(copy.buttons.futures, "settings_market:futures"),
        ],
        [Markup.button.callback(copy.buttons.back, "settings:home")],
      ]),
    };
  }

  if (step === "settings-style") {
    return {
      kind: "text",
      text: copy.settingsStyleMessage,
      extra: Markup.inlineKeyboard([
        [
          Markup.button.callback(copy.buttons.scalping, "settings_style:scalping"),
          Markup.button.callback(copy.buttons.intraday, "settings_style:intraday"),
        ],
        [Markup.button.callback(copy.buttons.back, "settings:home")],
      ]),
    };
  }

  if (step === "settings-coins") {
    const coins = Array.isArray(user.coins) ? user.coins : [];
    const selectedLine = coins.length ? `\n${copy.selectedLabel}: ${coins.join(", ")}` : "";

    return {
      kind: "text",
      text: `${copy.settingsCoinsMessage}\n\n${copy.selectionLabel}: ${coins.length}/3${selectedLine}`,
      extra: Markup.inlineKeyboard(
        buildCoinKeyboard("settings_coin", coins, true, "settings:home", copy),
      ),
    };
  }

  if (step === "help") {
    return {
      kind: "text",
      text: buildHelpText(copy, user),
      extra: Markup.inlineKeyboard([
        [Markup.button.callback(copy.buttons.back, "settings:back")],
      ]),
    };
  }

  return {
    kind: "text",
    text: buildWelcomeText(copy, user),
    extra: Markup.inlineKeyboard([
      [
        Markup.button.callback(copy.buttons.market, "menu:market"),
        Markup.button.callback(copy.buttons.signals, "menu:signals"),
      ],
      [
        Markup.button.callback(copy.buttons.scanner, "menu:scanner"),
        Markup.button.callback(copy.buttons.alerts, "menu:alerts"),
      ],
      [
        Markup.button.callback(copy.buttons.settings, "menu:settings"),
        Markup.button.callback(copy.buttons.help, "menu:help"),
      ],
    ]),
  };
}

function buildMarketScreen(copy, marketOverview, user) {
  return {
    kind: "text",
    text: buildMarketText(copy, marketOverview, user?.level),
    extra: Markup.inlineKeyboard([
      [Markup.button.callback(copy.buttons.marketBack, "market:back")],
    ]),
  };
}

function buildSignalsScreen(copy, signalsOverview, user) {
  return {
    kind: "text",
    text: buildSignalsText(copy, signalsOverview, user?.level),
    extra: Markup.inlineKeyboard([
      [Markup.button.callback(copy.buttons.marketBack, "signals:back")],
    ]),
  };
}

function buildAlertsScreen(copy, alertsOverview, user) {
  return {
    kind: "text",
    text: buildAlertsText(copy, alertsOverview, user?.level),
    extra: buildAlertsKeyboard(copy, user),
  };
}

function buildScannerScreen(copy, scannerOverview, user) {
  return {
    kind: "text",
    text: buildScannerText(copy, scannerOverview, user?.level),
    extra: Markup.inlineKeyboard([
      [Markup.button.callback(copy.buttons.marketBack, "scanner:back")],
    ]),
  };
}

function getErrorMessage(error) {
  if (error && typeof error.description === "string") {
    return error.description;
  }

  if (error && typeof error.message === "string") {
    return error.message;
  }

  return "";
}

function isExpiredCallbackError(error) {
  const message = getErrorMessage(error);
  return message.includes("query is too old") || message.includes("query ID is invalid");
}

async function safeAnswerCbQuery(ctx, ...args) {
  if (!ctx.callbackQuery) {
    return;
  }

  try {
    await ctx.answerCbQuery(...args);
  } catch (error) {
    if (!isExpiredCallbackError(error)) {
      throw error;
    }
  }
}

async function deleteActiveMessage(ctx, user, exceptMessageId = null) {
  const messageId = user.active_message_id;

  if (!messageId || messageId === exceptMessageId) {
    return;
  }

  try {
    await ctx.telegram.deleteMessage(ctx.chat.id, messageId);
  } catch (error) {
    const message = getErrorMessage(error);
    // Ignorer si le message a déjà été supprimé — loguer toute autre erreur
    if (!message.includes("message to delete not found")) {
      console.warn(`[deleteActiveMessage] Impossible de supprimer msg ${messageId}:`, message);
    }
  }
}

async function renderStep(ctx, user, step) {
  const screen = buildScreen(user, step);
  const callbackMessageId = ctx.callbackQuery?.message?.message_id || null;

  if (ctx.callbackQuery && screen.kind === "text") {
    try {
      await ctx.editMessageText(screen.text, screen.extra);
      user.active_message_id = callbackMessageId;
      await saveUser(user);
      await safeAnswerCbQuery(ctx);
      return;
    } catch (error) {
      const message = getErrorMessage(error);

      if (message.includes("message is not modified")) {
        user.active_message_id = callbackMessageId;
        await saveUser(user);
        await safeAnswerCbQuery(ctx);
        return;
      }
    }
  }

  await deleteActiveMessage(ctx, user, callbackMessageId);
  let sentMessage;

  if (screen.kind === "photo") {
    sentMessage = await ctx.replyWithPhoto(screen.media, {
      caption: screen.caption,
      reply_markup: screen.extra.reply_markup,
    });
  } else if (screen.kind === "video") {
    sentMessage = await ctx.replyWithVideo(screen.media, {
      caption: screen.caption,
      reply_markup: screen.extra.reply_markup,
    });
  } else {
    sentMessage = await ctx.reply(screen.text, screen.extra);
  }

  user.active_message_id = sentMessage.message_id;
  await saveUser(user);

  if (ctx.callbackQuery) {
    await safeAnswerCbQuery(ctx);
  }
}

async function renderMarketOverview(ctx, user) {
  const copy = getCopy(user.language);
  const marketOverview = await getMarketOverview(user.user_id);
  const screen = buildMarketScreen(copy, marketOverview, user);
  const callbackMessageId = ctx.callbackQuery?.message?.message_id || null;

  if (ctx.callbackQuery) {
    try {
      await ctx.editMessageText(screen.text, screen.extra);
      user.active_message_id = callbackMessageId;
      await saveUser(user);
      await safeAnswerCbQuery(ctx);
      return;
    } catch (error) {
      const message = getErrorMessage(error);
      if (message.includes("message is not modified")) {
        await safeAnswerCbQuery(ctx);
        return;
      }
    }
  }

  await deleteActiveMessage(ctx, user, callbackMessageId);
  const sentMessage = await ctx.reply(screen.text, screen.extra);
  user.active_message_id = sentMessage.message_id;
  await saveUser(user);

  if (ctx.callbackQuery) {
    await safeAnswerCbQuery(ctx);
  }
}

async function renderSignalsOverview(ctx, user) {
  const copy = getCopy(user.language);
  const signalsOverview = await getSignalsOverview(user.user_id);
  const screen = buildSignalsScreen(copy, signalsOverview, user);
  const callbackMessageId = ctx.callbackQuery?.message?.message_id || null;

  if (ctx.callbackQuery) {
    try {
      await ctx.editMessageText(screen.text, screen.extra);
      user.active_message_id = callbackMessageId;
      await saveUser(user);
      await safeAnswerCbQuery(ctx);
      return;
    } catch (error) {
      const message = getErrorMessage(error);
      if (message.includes("message is not modified")) {
        await safeAnswerCbQuery(ctx);
        return;
      }
    }
  }

  await deleteActiveMessage(ctx, user, callbackMessageId);
  const sentMessage = await ctx.reply(screen.text, screen.extra);
  user.active_message_id = sentMessage.message_id;
  await saveUser(user);

  if (ctx.callbackQuery) {
    await safeAnswerCbQuery(ctx);
  }
}

async function renderAlertsOverview(ctx, user) {
  const copy = getCopy(user.language);
  const alertsOverview = await getAlertsOverview(user.user_id);
  const screen = buildAlertsScreen(copy, alertsOverview, user);
  const callbackMessageId = ctx.callbackQuery?.message?.message_id || null;

  if (ctx.callbackQuery) {
    try {
      await ctx.editMessageText(screen.text, screen.extra);
      user.active_message_id = callbackMessageId;
      await saveUser(user);
      await safeAnswerCbQuery(ctx);
      return;
    } catch (error) {
      const message = getErrorMessage(error);
      if (message.includes("message is not modified")) {
        await safeAnswerCbQuery(ctx);
        return;
      }
    }
  }

  await deleteActiveMessage(ctx, user, callbackMessageId);
  const sentMessage = await ctx.reply(screen.text, screen.extra);
  user.active_message_id = sentMessage.message_id;
  await saveUser(user);

  if (ctx.callbackQuery) {
    await safeAnswerCbQuery(ctx);
  }
}

async function renderScannerOverview(ctx, user) {
  const copy = getCopy(user.language);
  const scannerOverview = await getScannerOverview(user.user_id);
  const screen = buildScannerScreen(copy, scannerOverview, user);
  const callbackMessageId = ctx.callbackQuery?.message?.message_id || null;

  if (ctx.callbackQuery) {
    try {
      await ctx.editMessageText(screen.text, screen.extra);
      user.active_message_id = callbackMessageId;
      await saveUser(user);
      await safeAnswerCbQuery(ctx);
      return;
    } catch (error) {
      const message = getErrorMessage(error);
      if (message.includes("message is not modified")) {
        await safeAnswerCbQuery(ctx);
        return;
      }
    }
  }

  await deleteActiveMessage(ctx, user, callbackMessageId);
  const sentMessage = await ctx.reply(screen.text, screen.extra);
  user.active_message_id = sentMessage.message_id;
  await saveUser(user);

  if (ctx.callbackQuery) {
    await safeAnswerCbQuery(ctx);
  }
}

let alertPollingInFlight = false;
let alertPollingTimer = null;
let tradePollingInFlight = false;
let tradePollingTimer = null;
let isBotRunning = false;
let isBotLaunching = false;
let launchStarted = false;
let botRetryTimer = null;
let botStartAttempt = 0;
let healthServerStarted = false;

async function pollAlertDeliveryJobs() {
  if (alertPollingInFlight) {
    return;
  }

  alertPollingInFlight = true;

  try {
    const jobs = await getAlertDeliveryJobs();

    for (const job of jobs) {
      const copy = getCopy(job.language);
      await bot.telegram.sendMessage(job.user_id, buildAlertsText(copy, job, job.level));
      await acknowledgeAlertDelivery(job.user_id, job.digest_key);
    }
  } catch (error) {
    console.error("Alert delivery poll failed:", error);
  } finally {
    alertPollingInFlight = false;
  }
}

function startAlertDeliveryLoop() {
  if (alertPollingTimer) {
    return;
  }

  console.log(`Alert delivery polling every ${ALERT_POLLING_INTERVAL_MS}ms.`);
  void pollAlertDeliveryJobs();
  alertPollingTimer = setInterval(() => {
    void pollAlertDeliveryJobs();
  }, ALERT_POLLING_INTERVAL_MS);
}

async function pollTradeManagementJobs() {
  if (tradePollingInFlight) {
    return;
  }

  tradePollingInFlight = true;

  try {
    const jobs = await getTradeManagementJobs();

    for (const job of jobs) {
      await bot.telegram.sendMessage(job.user_id, formatTradeManagementTelegramMessage(job));
      await acknowledgeTradeManagementEvent(job.user_id, job.event_key);
    }
  } catch (error) {
    console.error("Trade management poll failed:", error);
  } finally {
    tradePollingInFlight = false;
  }
}

function startTradeManagementLoop() {
  if (tradePollingTimer) {
    return;
  }

  console.log(`Trade management polling every ${ALERT_POLLING_INTERVAL_MS}ms.`);
  void pollTradeManagementJobs();
  tradePollingTimer = setInterval(() => {
    void pollTradeManagementJobs();
  }, ALERT_POLLING_INTERVAL_MS);
}

function startHealthServer() {
  if (!PORT || healthServerStarted) {
    return;
  }

  const server = http.createServer((req, res) => {
    if (req.url === "/api/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok", service: "scannerht-bot" }));
      return;
    }

    res.writeHead(200, { "Content-Type": "text/plain" });
    res.end("scannerht-bot");
  });

  server.listen(PORT, "0.0.0.0", () => {
    console.log(`Bot health server listening on ${PORT}.`);
  });
  healthServerStarted = true;
}

const bot = new Telegraf(BOT_TOKEN);

bot.start(async (ctx) => {
  try {
    const user = await getUser(ctx.from.id);
    refreshCompletion(user);
    await saveUser(user);
    const nextStep = getNextStep(user);
    await renderStep(ctx, user, nextStep);
  } catch (error) {
    console.error("[bot.start] Erreur:", error);
    await ctx.reply("\u26a0\ufe0f Service temporairement indisponible. R\u00e9essaie dans quelques instants.").catch(() => {});
  }
});

bot.command("reset", async (ctx) => {
  try {
    const existingUser = await getUser(ctx.from.id);
    const user = getDefaultUser(ctx.from.id);
    user.active_message_id = existingUser.active_message_id;
    await saveUser(user);
    await renderStep(ctx, user, "language");
  } catch (error) {
    console.error("[bot.reset] Erreur:", error);
    await ctx.reply("\u26a0\ufe0f Impossible de r\u00e9initialiser pour l'instant.").catch(() => {});
  }
});

bot.action(/^lang:(fr|en|es)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  user.language = ctx.match[1];
  user.level = null;
  user.scanner_limit = null;
  user.market = null;
  user.trading_style = null;
  user.coins = [];
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "level");
});

bot.action(/^level:(beginner|medium|pro)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);

  if (!user.language) {
    await renderStep(ctx, user, "language");
    return;
  }

  user.level = ctx.match[1];
  syncScannerLimitByLevel(user, true);
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "market");
});

bot.action(/^intro:begin$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  user.intro_seen = true;
  refreshCompletion(user);
  await saveUser(user);

  const nextStep = user.onboarding_complete ? "welcome" : getNextStep(user);
  await renderStep(ctx, user, nextStep);
});

bot.action(/^market:(spot|futures)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);

  if (!user.language) {
    await renderStep(ctx, user, "language");
    return;
  }

  user.market = ctx.match[1];
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "style");
});

bot.action(/^style:(scalping|intraday)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);

  if (!user.language) {
    await renderStep(ctx, user, "language");
    return;
  }

  if (!user.market) {
    await renderStep(ctx, user, "market");
    return;
  }

  user.trading_style = ctx.match[1];
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "coins");
});

bot.action(/^coin:([A-Z0-9]+)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  const copy = getCopy(user.language);
  const selectedCoin = ctx.match[1];
  const isKnownCoin = COINS.some((coin) => coin.symbol === selectedCoin);

  if (!user.language) {
    await renderStep(ctx, user, "language");
    return;
  }

  if (!user.market) {
    await renderStep(ctx, user, "market");
    return;
  }

  if (!user.trading_style) {
    await renderStep(ctx, user, "style");
    return;
  }

  if (!isKnownCoin) {
    await safeAnswerCbQuery(ctx);
    return;
  }

  if (!Array.isArray(user.coins)) {
    user.coins = [];
  }

  if (user.coins.includes(selectedCoin)) {
    user.coins = user.coins.filter((coin) => coin !== selectedCoin);
  } else if (user.coins.length < 3) {
    user.coins.push(selectedCoin);
  } else {
    await safeAnswerCbQuery(ctx, copy.maxCoins);
    return;
  }

  refreshCompletion(user);
  await saveUser(user);

  if (user.onboarding_complete) {
    await renderStep(ctx, user, "welcome");
    return;
  }

  await renderStep(ctx, user, "coins");
});

bot.action(/^settings:(language|level|scanner_limit|market|style|coins|home)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);

  if (!user.onboarding_complete) {
    await renderStep(ctx, user, getNextStep(user));
    return;
  }

  const screenByAction = {
    language: "settings-language",
    level: "settings-level",
    scanner_limit: "settings-scanner-limit",
    market: "settings-market",
    style: "settings-style",
    coins: "settings-coins",
    home: "settings-home",
  };

  if (ctx.match[1] === "scanner_limit" && user.level !== "pro") {
    await renderStep(ctx, user, "settings-home");
    return;
  }

  await renderStep(ctx, user, screenByAction[ctx.match[1]]);
});

bot.action(/^settings_lang:(fr|en|es)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  user.language = ctx.match[1];
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "settings-home");
});

bot.action(/^settings_level:(beginner|medium|pro)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  user.level = ctx.match[1];
  syncScannerLimitByLevel(user, true);
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "settings-home");
});

bot.action(/^settings_scanner_limit:(3|4|5|6|7|8)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  if (user.level !== "pro") {
    await renderStep(ctx, user, "settings-home");
    return;
  }

  user.scanner_limit = Number(ctx.match[1]);
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "settings-home");
});

bot.action(/^settings_market:(spot|futures)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  user.market = ctx.match[1];
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "settings-home");
});

bot.action(/^settings_style:(scalping|intraday)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  user.trading_style = ctx.match[1];
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "settings-home");
});

bot.action(/^settings_coin:([A-Z0-9]+)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  const copy = getCopy(user.language);
  const selectedCoin = ctx.match[1];
  const isKnownCoin = COINS.some((coin) => coin.symbol === selectedCoin);

  if (!isKnownCoin) {
    await safeAnswerCbQuery(ctx);
    return;
  }

  if (!Array.isArray(user.coins)) {
    user.coins = [];
  }

  if (user.coins.includes(selectedCoin)) {
    user.coins = user.coins.filter((coin) => coin !== selectedCoin);
  } else if (user.coins.length < 3) {
    user.coins.push(selectedCoin);
  } else {
    await safeAnswerCbQuery(ctx, copy.maxCoins);
    return;
  }

  refreshCompletion(user);
  await saveUser(user);

  if (user.coins.length === 3) {
    await renderStep(ctx, user, "settings-home");
    return;
  }

  await renderStep(ctx, user, "settings-coins");
});

bot.action(/^settings:reset$/, async (ctx) => {
  const existingUser = await getUser(ctx.from.id);
  const user = getDefaultUser(ctx.from.id);
  user.intro_seen = true;
  user.active_message_id = existingUser.active_message_id;
  await saveUser(user);
  await renderStep(ctx, user, "language");
});

bot.action(/^settings:back$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "welcome");
});

bot.action(/^market:back$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "welcome");
});

bot.action(/^signals:back$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "welcome");
});

bot.action(/^alerts:back$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "welcome");
});

bot.action(/^scanner:back$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  refreshCompletion(user);
  await saveUser(user);
  await renderStep(ctx, user, "welcome");
});

bot.action(/^alerts_toggle:(on|off)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  user.alerts_enabled = ctx.match[1] === "on";
  refreshCompletion(user);
  await saveUser(user);
  await renderAlertsOverview(ctx, user);
});

bot.action(/^alerts_priority:(high|medium|low)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  const copy = getCopy(user.language);
  if (getUserLevel(user) !== "pro") {
    await safeAnswerCbQuery(ctx, copy.feedback.alertsPriorityLocked);
    await renderAlertsOverview(ctx, user);
    return;
  }
  user.alerts_min_priority = ctx.match[1];
  refreshCompletion(user);
  await saveUser(user);
  await renderAlertsOverview(ctx, user);
});

bot.action(/^menu:(market|signals|scanner|alerts|settings|help)$/, async (ctx) => {
  const user = await getUser(ctx.from.id);
  const copy = getCopy(user.language);
  const section = ctx.match[1];

  if (section === "market") {
    await renderMarketOverview(ctx, user);
    return;
  }

  if (section === "signals") {
    await renderSignalsOverview(ctx, user);
    return;
  }

  if (section === "alerts") {
    await renderAlertsOverview(ctx, user);
    return;
  }

  if (section === "scanner") {
    await renderScannerOverview(ctx, user);
    return;
  }

  if (section === "settings") {
    await renderStep(ctx, user, "settings-home");
    return;
  }

  if (section === "help") {
    await renderStep(ctx, user, "help");
    return;
  }

  await safeAnswerCbQuery(ctx, copy.menuFeedback[section]);
});

bot.catch((error) => {
  if (isExpiredCallbackError(error)) {
    console.warn("Ignoring expired Telegram callback query.");
    return;
  }
  console.error("Unhandled bot error:", error);
});

bot.on("message", async (ctx) => {
  try {
    const user = await getUser(ctx.from.id);
    refreshCompletion(user);
    await saveUser(user);
    const nextStep = getNextStep(user);
    await renderStep(ctx, user, nextStep);
  } catch (error) {
    console.error("[bot.message] Erreur:", error);
    await ctx.reply("\u26a0\ufe0f Service momentan\u00e9ment indisponible.").catch(() => {});
  }
});

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function launchBotWithTimeout(timeoutMs = 15_000) {
  return Promise.race([
    bot.launch(),
    new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error("bot_launch_timeout"));
      }, timeoutMs);
    }),
  ]);
}

function getLaunchErrorMessage(error) {
  return error?.description || error?.message || String(error);
}

function isPollingConflictError(error) {
  return error?.response?.error_code === 409 || getLaunchErrorMessage(error).includes("409");
}

function getRetryDelayMs(error) {
  const jitterMs = Math.floor(Math.random() * 2001);
  if (isPollingConflictError(error)) {
    return 8000 + jitterMs;
  }

  const baseDelayMs = Math.min(30_000, 2000 * 2 ** Math.max(0, botStartAttempt - 1));
  return Math.min(30_000, baseDelayMs + jitterMs);
}

function scheduleBotRetry(delayMs) {
  if (botRetryTimer) {
    clearTimeout(botRetryTimer);
  }

  botRetryTimer = setTimeout(() => {
    botRetryTimer = null;
    void startBot();
  }, delayMs);
}

async function stopBotForRetry(reason) {
  if (!isBotRunning) {
    return;
  }

  try {
    await bot.stop(reason);
  } catch (error) {
    console.warn("Bot stop before relaunch failed:", getLaunchErrorMessage(error));
  } finally {
    isBotRunning = false;
  }
}

async function startBot() {
  if (isBotRunning || isBotLaunching) {
    return;
  }

  isBotLaunching = true;
  botStartAttempt += 1;

  console.log("Starting bot init...");
  console.log(BOT_TOKEN ? "Bot token loaded" : "Bot token missing");
  console.log("Launching bot...");

  try {
    await stopBotForRetry("relaunch");
    if (launchStarted) {
      console.log("bot.launch() already started, skipping duplicate launch");
      return;
    }
    launchStarted = true;
    console.log("Calling bot.launch()...");
    await launchBotWithTimeout(15_000);
    console.log("bot.launch() resolved");
    isBotRunning = true;
    botStartAttempt = 0;
    startHealthServer();
    startAlertDeliveryLoop();
    startTradeManagementLoop();
    console.log("ScannerHT bot is running");
    console.log("Polling is active");
    console.log("ScannerHT bot is running. Press Ctrl+C to stop.");
  } catch (error) {
    isBotRunning = false;
    launchStarted = false;
    if (error?.message === "bot_launch_timeout") {
      console.error("bot.launch() timeout - likely polling conflict or Telegram connection issue");
      process.exit(1);
    }
    const delayMs = getRetryDelayMs(error);
    const delaySeconds = (delayMs / 1000).toFixed(1);
    const errorMessage = getLaunchErrorMessage(error);
    const errorDetails = error?.stack || error;

    if (isPollingConflictError(error)) {
      console.warn(`Telegram polling conflict detected (${errorMessage}); retrying polling in ${delaySeconds}s.`);
      console.warn("bot.launch() failed details:", errorDetails);
    } else {
      console.error(`Bot launch failed (${errorMessage}); retrying polling in ${delaySeconds}s.`);
      console.error("bot.launch() failed details:", errorDetails);
    }

    scheduleBotRetry(delayMs);
  } finally {
    if (!isBotRunning) {
      launchStarted = false;
    }
    isBotLaunching = false;
  }
}

void startBot();

process.once("SIGINT", async () => {
  if (botRetryTimer) {
    clearTimeout(botRetryTimer);
    botRetryTimer = null;
  }
  await stopBotForRetry("SIGINT");
});
process.once("SIGTERM", async () => {
  if (botRetryTimer) {
    clearTimeout(botRetryTimer);
    botRetryTimer = null;
  }
  await stopBotForRetry("SIGTERM");
});
