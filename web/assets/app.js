const appRoot = document.getElementById("app");
const sessionButton = document.getElementById("session-button");
const API_BASE_URL = `${window.location.origin}/api`;

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
  BTC: "COINBASE:BTCUSD",
  ETH: "COINBASE:ETHUSD",
  SOL: "COINBASE:SOLUSD",
  DOGE: "COINBASE:DOGEUSD",
  AVAX: "COINBASE:AVAXUSD",
  MATIC: "COINBASE:POLUSD",
  LINK: "COINBASE:LINKUSD",
  DOT: "COINBASE:DOTUSD",
};

const copy = {
  fr: {
    locale: "fr",
    authEyebrow: "Connexion",
    authTitle: "Connecte-toi avec Telegram",
    authCopy: "Ton compte web reprendra automatiquement le meme contexte que ton bot Telegram.",
    authHint: "Configure aussi le domaine du widget dans BotFather avec /setdomain.",
    authUnavailable: "Le login Telegram n'est pas encore configure sur ce serveur.",
    authLogout: "Se deconnecter",
    authStatus: "Session Telegram active",
    loading: "Connexion au cockpit...",
    languageTitle: "Choisis ta langue",
    levelTitle: "Choisis ton niveau",
    marketTitle: "Choisis ton marche",
    styleTitle: "Quel est ton style de trading ?",
    coinsTitle: "Choisis 3 cryptos a suivre",
    coinsHint: "Selection",
    welcomeTitle: "Ton assistant crypto est pret.",
    welcomeCopy: "Fonctions disponibles",
    settingsTitle: "Reglages",
    settingsCopy: "Ajuste ton profil sans quitter l'ecran principal.",
    desks: {
      market: {
        eyebrow: "Marche | Contexte",
        role: "Lire l'environnement avant de prendre un trade.",
        question: "Question: est-ce que le marche aide ou complique les decisions ?",
        chartTitle: "Contexte du marche",
        noteTitle: "Note contexte",
      },
      signals: {
        eyebrow: "Signaux | Decision",
        role: "Decider ce qui merite une action maintenant.",
        question: "Question: quel setup merite vraiment une entree ?",
        chartTitle: "Execution",
        noteTitle: "Note execution",
      },
      alerts: {
        eyebrow: "Alertes | Rappel",
        role: "Revenir seulement quand quelque chose devient utile.",
        question: "Question: quand faut-il revenir sur le marche ?",
        chartTitle: "Zone d'alerte",
        noteTitle: "Note livraison",
      },
      scanner: {
        eyebrow: "Scanner | Surveillance",
        role: "Classer ce qu'il faut surveiller ensuite.",
        question: "Question: quelle idee monte dans la file d'attention ?",
        chartTitle: "File de surveillance",
        noteTitle: "Note scan",
      },
    },
    scanner: {
      title: "Scanner",
      hot: "Chaud",
      building: "Construction",
      early: "Tot",
      score: "Score",
      urgency: "Urgence",
      trigger: "Declencheur",
      invalidation: "Invalidation",
      alerts: "Alertes",
      armed: "Armees",
      off: "Coupees",
      selected: "Liste suivie",
      discovery: "Decouverte",
      watch: "Scanner actif",
    },
    settingsActions: {
      language: "Langue",
      level: "Niveau",
      scannerLimit: "Scanner",
      market: "Marche",
      style: "Style",
      coins: "Cryptos",
      reset: "Recommencer",
      back: "Retour",
    },
    labels: {
      language: "Langue",
      level: "Niveau",
      scannerLimit: "Scanner",
      market: "Marche",
      style: "Style",
      coins: "Cryptos",
      unset: "Non defini",
      welcome: "Pret",
      account: "Compte",
    },
    alerts: {
      prefsTitle: "Livraison Telegram",
      armed: "Alertes armees",
      disarmed: "Alertes arretees",
      cooldown: "Cooldown actif",
      arm: "Armer les alerts",
      disarm: "Couper les alerts",
      priority: "Priorite minimum",
      lastSent: "Dernier envoi",
      nextWindow: "Prochaine fenetre",
      quiet: "Prete",
      high: "Haute",
      medium: "Moyenne",
      low: "Basse",
      status: "Statut",
    },
    menu: [
      { key: "market", icon: "📊", title: "Marche", description: "Lire le contexte" },
      { key: "signals", icon: "🎯", title: "Signaux", description: "Decider quoi trader" },
      { key: "scanner", icon: "📡", title: "Scanner", description: "Surveiller quoi ensuite" },
      { key: "alerts", icon: "🚨", title: "Alertes", description: "Savoir quand revenir" },
      { key: "settings", icon: "⚙", title: "Reglages", description: "Configuration du profil" },
      { key: "help", icon: "❓", title: "Aide", description: "Aide rapide" },
    ],
    values: {
      language: { fr: "Francais", en: "English", es: "Espanol" },
      level: { beginner: "Debutant", medium: "Moyen", pro: "Pro" },
      market: { spot: "Spot", futures: "Futures" },
      style: { scalping: "Scalping", intraday: "Intraday" },
    },
    limitCoins: "Tu peux suivre exactement 3 cryptos.",
    ui: {
      setup: "Configuration",
      introEyebrow: "Entree officielle",
      languageSetupCopy: "Choisis la langue de l'interface pour ton cockpit crypto.",
      levelSetupCopy: "Choisis le niveau de guidage que tu veux recevoir de l'assistant.",
      marketSetupCopy: "Choisis le contexte de marche que l'assistant doit prioriser.",
      styleSetupCopy: "Ton style aide a regler le rythme des futurs signaux et vues.",
      chartEyebrow: "Graphique",
      chartLinkSuffix: "graphique",
      byTradingView: "par TradingView",
      scannerCountCopy: "Choisis combien d'idees Scanner peuvent apparaitre en meme temps.",
      topFocus: "Focus principal",
      action: "Action",
      trigger: "Declencheur",
      size: "Taille",
      distance: "Distance",
      price: "Prix",
      volume: "Volume",
      origin: "Origine",
      confidence: "Confiance",
      conviction: "Conviction",
      timeframe: "Horizon",
      risk: "Risque",
      focus: "Focus",
      queue: "File",
      none: "Aucun",
      never: "Jamais",
      shown: "affiches",
      auto: "auto",
      coinsUnit: "cryptos",
      contextFirst: "Contexte d'abord",
      marketInsightTitle: "Lire le contexte d'abord",
      marketInsightBody: "Commence ici pour savoir si l'environnement aide ou complique tes decisions.",
      signalsInsightTitle: "Decider quoi trader",
      signalsInsightBody: "Cet ecran sert a l'execution, pas a parcourir toutes les idees.",
      scannerInsightTitle: "Classer quoi surveiller ensuite",
      scannerInsightBody: "Utilise Scanner quand tu veux une file d'attention, pas plus de bruit.",
      alertsInsightTitle: "Revenir au bon moment",
      alertsInsightBody: "Les alertes protegent ton attention et evitent de surveiller le chart sans arret.",
      profileEyebrow: "Profil",
      levelBehavior: "Ton niveau change le produit, pas seulement les textes.",
      currentWatchlist: "Liste suivie actuelle",
      languageField: "Langue",
      marketField: "Marche",
      styleField: "Style",
      signalsSingle: "Signaux a focus unique.",
      signalsGuided: "Signaux guides.",
      signalsDense: "Signaux denses et configurables.",
      helpEyebrow: "Aide",
      helpTitle: "Utilise le produit dans cet ordre",
      helpCopy: "Lis d'abord le contexte, puis decide, puis scanne, puis laisse les alertes te faire revenir au bon moment.",
      oneMainSetup: "Un setup principal",
      executionReady: "Setups prets a executer",
      simpleAction: "Action simple",
      riskInvalidation: "Risque et invalidation",
      threshold: "Seuil",
      deliveryStatus: "Statut de livraison",
      nextReturnWindow: "Prochaine fenetre de retour",
      decisionLine: "Ligne de decision",
      highPriorityOnly: "Haute priorite seulement",
      returnOnlyOnTrigger: "Retour seulement sur declencheur",
      watchClosest: "Surveille seulement ce qui est le plus proche",
      cockpit: "Cockpit",
      sourceLabel: "Source",
      updatedLabel: "Mis a jour",
      roleLabel: "Role",
      questionLabel: "Question",
      nextActionLabel: "Action suivante",
      visibleCryptoCount: "Nombre de cryptos visibles",
      save: "Enregistrer",
      regime: "Regime",
      sentiment: "Sentiment",
      volatility: "Volatilite",
      focusWindow: "Fenetre de focus",
      topSetup: "Setup principal",
      riskPosture: "Posture de risque",
      discovery: "Decouverte",
      triggerPlan: "Plan de declenchement",
      alertReadiness: "Preparation des alertes",
      threeIdeasMax: "3 idees max",
      modulePending: "arrive dans la prochaine connexion du module.",
    },
  },
  en: {
    locale: "en",
    authEyebrow: "Authentication",
    authTitle: "Sign in with Telegram",
    authCopy: "Your web account will automatically resume the same context as your Telegram bot.",
    authHint: "Also configure the widget domain in BotFather with /setdomain.",
    authUnavailable: "Telegram login is not configured on this server yet.",
    authLogout: "Log out",
    authStatus: "Telegram session active",
    loading: "Connecting to the cockpit...",
    languageTitle: "Choose your language",
    levelTitle: "Choose your level",
    marketTitle: "Choose your market",
    styleTitle: "What is your trading style?",
    coinsTitle: "Choose 3 cryptos to track",
    coinsHint: "Selection",
    welcomeTitle: "Your crypto assistant is ready.",
    welcomeCopy: "Available features",
    settingsTitle: "Settings",
    settingsCopy: "Adjust your profile without leaving the main screen.",
    desks: {
      market: {
        eyebrow: "Market | Context",
        role: "Read the environment before taking risk.",
        question: "Question: is the market helping or fighting your decisions?",
        chartTitle: "Live context",
        noteTitle: "Context note",
      },
      signals: {
        eyebrow: "Signals | Decision",
        role: "Decide what deserves action now.",
        question: "Question: which setup is worth an entry now?",
        chartTitle: "Live execution",
        noteTitle: "Execution note",
      },
      alerts: {
        eyebrow: "Alerts | Return",
        role: "Come back only when something deserves attention.",
        question: "Question: when should you return to the market?",
        chartTitle: "Alert zone",
        noteTitle: "Delivery note",
      },
      scanner: {
        eyebrow: "Scanner | Watch next",
        role: "Rank what deserves attention next.",
        question: "Question: which idea is moving up the queue?",
        chartTitle: "Watch queue",
        noteTitle: "Scan note",
      },
    },
    scanner: {
      title: "Scanner",
      hot: "Hot",
      building: "Building",
      early: "Early",
      score: "Score",
      urgency: "Urgency",
      trigger: "Trigger",
      invalidation: "Invalidation",
      alerts: "Alerts",
      armed: "Armed",
      off: "Off",
      selected: "Watchlist",
      discovery: "Discovery",
      watch: "Scanner live",
    },
    settingsActions: {
      language: "Language",
      level: "Level",
      scannerLimit: "Scanner",
      market: "Market",
      style: "Style",
      coins: "Coins",
      reset: "Restart",
      back: "Back",
    },
    labels: {
      language: "Language",
      level: "Level",
      scannerLimit: "Scanner",
      market: "Market",
      style: "Style",
      coins: "Coins",
      unset: "Not set",
      welcome: "Ready",
      account: "Account",
    },
    alerts: {
      prefsTitle: "Telegram delivery",
      armed: "Alerts armed",
      disarmed: "Alerts off",
      cooldown: "Cooldown active",
      arm: "Arm alerts",
      disarm: "Pause alerts",
      priority: "Minimum priority",
      lastSent: "Last sent",
      nextWindow: "Next window",
      quiet: "Ready",
      high: "High",
      medium: "Medium",
      low: "Low",
      status: "Status",
    },
    menu: [
      { key: "market", icon: "📊", title: "Market", description: "Read the context" },
      { key: "signals", icon: "🎯", title: "Signals", description: "Decide what to trade" },
      { key: "scanner", icon: "📡", title: "Scanner", description: "Watch what comes next" },
      { key: "alerts", icon: "🚨", title: "Alerts", description: "Know when to come back" },
      { key: "settings", icon: "⚙", title: "Settings", description: "Profile controls" },
      { key: "help", icon: "❓", title: "Help", description: "Quick guidance" },
    ],
    values: {
      language: { fr: "Francais", en: "English", es: "Espanol" },
      level: { beginner: "Beginner", medium: "Medium", pro: "Pro" },
      market: { spot: "Spot", futures: "Futures" },
      style: { scalping: "Scalping", intraday: "Intraday" },
    },
    limitCoins: "You can track exactly 3 cryptos.",
    ui: {
      setup: "Setup",
      introEyebrow: "Official entry",
      languageSetupCopy: "Pick the interface language for your crypto cockpit.",
      levelSetupCopy: "Choose the level of guidance you want from the assistant.",
      marketSetupCopy: "Choose the market context you want the assistant to prioritize.",
      styleSetupCopy: "Your style helps tailor the pace of future signals and views.",
      chartEyebrow: "Chart",
      chartLinkSuffix: "chart",
      byTradingView: "by TradingView",
      scannerCountCopy: "Choose how many Scanner ideas can be shown at once.",
      topFocus: "Top focus",
      action: "Action",
      trigger: "Trigger",
      size: "Size",
      distance: "Distance",
      price: "Price",
      volume: "Volume",
      origin: "Origin",
      confidence: "Confidence",
      conviction: "Conviction",
      timeframe: "Timeframe",
      risk: "Risk",
      focus: "Focus",
      queue: "Queue",
      none: "None",
      never: "Never",
      shown: "shown",
      auto: "auto",
      coinsUnit: "coins",
      contextFirst: "Context first",
      marketInsightTitle: "Read context first",
      marketInsightBody: "Start here when you want to know if conditions are helping or fighting your decisions.",
      signalsInsightTitle: "Decide what deserves action",
      signalsInsightBody: "This screen is for execution quality, not for browsing every idea.",
      scannerInsightTitle: "Rank what to watch next",
      scannerInsightBody: "Use Scanner when you want a queue instead of more noise.",
      alertsInsightTitle: "Come back on time",
      alertsInsightBody: "Alerts are here to protect your focus and reduce chart babysitting.",
      profileEyebrow: "Profile",
      levelBehavior: "Your level changes product behavior, not just wording.",
      currentWatchlist: "Current watchlist",
      languageField: "Language",
      marketField: "Market",
      styleField: "Style",
      signalsSingle: "Signals stay single-focus.",
      signalsGuided: "Signals stay guided.",
      signalsDense: "Signals stay dense and configurable.",
      helpEyebrow: "Help",
      helpTitle: "Use the product in this order",
      helpCopy: "Read context first, then decide, then scan, then let alerts bring you back only when it matters.",
      oneMainSetup: "One main setup",
      executionReady: "Execution-ready setups",
      simpleAction: "Simple action",
      riskInvalidation: "Risk and invalidation",
      threshold: "Threshold",
      deliveryStatus: "Delivery status",
      nextReturnWindow: "Next return window",
      decisionLine: "Decision line",
      highPriorityOnly: "High priority only",
      returnOnlyOnTrigger: "Return only on trigger",
      watchClosest: "Watch only what is closest",
      cockpit: "Cockpit",
      sourceLabel: "Source",
      updatedLabel: "Updated",
      roleLabel: "Role",
      questionLabel: "Question",
      nextActionLabel: "Next action",
      visibleCryptoCount: "Visible crypto count",
      save: "Save",
      regime: "Regime",
      sentiment: "Sentiment",
      volatility: "Volatility",
      focusWindow: "Focus window",
      topSetup: "Top setup",
      riskPosture: "Risk posture",
      discovery: "Discovery",
      triggerPlan: "Trigger plan",
      alertReadiness: "Alert readiness",
      threeIdeasMax: "3 ideas max",
      modulePending: "is the next module to connect.",
    },
  },
  es: {
    locale: "es",
    authEyebrow: "Autenticacion",
    authTitle: "Conectate con Telegram",
    authCopy: "Tu cuenta web retomara automaticamente el mismo contexto que tu bot de Telegram.",
    authHint: "Configura tambien el dominio del widget en BotFather con /setdomain.",
    authUnavailable: "El login de Telegram no esta configurado todavia en este servidor.",
    authLogout: "Cerrar sesion",
    authStatus: "Sesion de Telegram activa",
    loading: "Conectando al cockpit...",
    languageTitle: "Elige tu idioma",
    levelTitle: "Elige tu nivel",
    marketTitle: "Elige tu mercado",
    styleTitle: "Cual es tu estilo de trading?",
    coinsTitle: "Elige 3 criptos para seguir",
    coinsHint: "Seleccion",
    welcomeTitle: "Tu asistente cripto esta listo.",
    welcomeCopy: "Funciones disponibles",
    settingsTitle: "Ajustes",
    settingsCopy: "Ajusta tu perfil sin salir de la pantalla principal.",
    desks: {
      market: {
        eyebrow: "Mercado | Contexto",
        role: "Leer el entorno antes de tomar riesgo.",
        question: "Pregunta: el mercado ayuda o complica tus decisiones?",
        chartTitle: "Contexto del mercado",
        noteTitle: "Nota contexto",
      },
      signals: {
        eyebrow: "Senales | Decision",
        role: "Decidir lo que merece accion ahora.",
        question: "Pregunta: que setup merece una entrada ahora?",
        chartTitle: "Ejecucion",
        noteTitle: "Nota ejecucion",
      },
      alerts: {
        eyebrow: "Alertas | Regreso",
        role: "Volver solo cuando algo merezca atencion.",
        question: "Pregunta: cuando deberias volver al mercado?",
        chartTitle: "Zona de alerta",
        noteTitle: "Nota entrega",
      },
      scanner: {
        eyebrow: "Scanner | Vigilancia",
        role: "Ordenar lo que merece atencion despues.",
        question: "Pregunta: que idea sube en la cola?",
        chartTitle: "Cola de vigilancia",
        noteTitle: "Nota scan",
      },
    },
    scanner: {
      title: "Scanner",
      hot: "Caliente",
      building: "Construyendo",
      early: "Temprano",
      score: "Score",
      urgency: "Urgencia",
      trigger: "Disparador",
      invalidation: "Invalidacion",
      alerts: "Alertas",
      armed: "Activas",
      off: "Pausadas",
      selected: "Lista seguida",
      discovery: "Descubrimiento",
      watch: "Scanner activo",
    },
    settingsActions: {
      language: "Idioma",
      level: "Nivel",
      scannerLimit: "Scanner",
      market: "Mercado",
      style: "Estilo",
      coins: "Criptos",
      reset: "Reiniciar",
      back: "Volver",
    },
    labels: {
      language: "Idioma",
      level: "Nivel",
      scannerLimit: "Scanner",
      market: "Mercado",
      style: "Estilo",
      coins: "Criptos",
      unset: "No definido",
      welcome: "Listo",
      account: "Cuenta",
    },
    alerts: {
      prefsTitle: "Entrega por Telegram",
      armed: "Alertas activadas",
      disarmed: "Alertas pausadas",
      cooldown: "Cooldown activo",
      arm: "Activar alertas",
      disarm: "Pausar alertas",
      priority: "Prioridad minima",
      lastSent: "Ultimo envio",
      nextWindow: "Proxima ventana",
      quiet: "Lista",
      high: "Alta",
      medium: "Media",
      low: "Baja",
      status: "Estado",
    },
    menu: [
      { key: "market", icon: "📊", title: "Mercado", description: "Leer el contexto" },
      { key: "signals", icon: "🎯", title: "Senales", description: "Decidir que operar" },
      { key: "scanner", icon: "📡", title: "Scanner", description: "Vigilar que sigue" },
      { key: "alerts", icon: "🚨", title: "Alertas", description: "Saber cuando volver" },
      { key: "settings", icon: "⚙", title: "Ajustes", description: "Control del perfil" },
      { key: "help", icon: "❓", title: "Ayuda", description: "Ayuda rapida" },
    ],
    values: {
      language: { fr: "Francais", en: "English", es: "Espanol" },
      level: { beginner: "Principiante", medium: "Medio", pro: "Pro" },
      market: { spot: "Spot", futures: "Futures" },
      style: { scalping: "Scalping", intraday: "Intraday" },
    },
    limitCoins: "Puedes seguir exactamente 3 criptos.",
    ui: {
      setup: "Configuracion",
      introEyebrow: "Entrada oficial",
      languageSetupCopy: "Elige el idioma de la interfaz para tu cockpit cripto.",
      levelSetupCopy: "Elige el nivel de guia que quieres del asistente.",
      marketSetupCopy: "Elige el contexto de mercado que el asistente debe priorizar.",
      styleSetupCopy: "Tu estilo ayuda a ajustar el ritmo de las futuras senales y vistas.",
      chartEyebrow: "Grafico",
      chartLinkSuffix: "grafico",
      byTradingView: "por TradingView",
      scannerCountCopy: "Elige cuantas ideas del Scanner pueden verse al mismo tiempo.",
      topFocus: "Foco principal",
      action: "Accion",
      trigger: "Disparador",
      size: "Tamano",
      distance: "Distancia",
      price: "Precio",
      volume: "Volumen",
      origin: "Origen",
      confidence: "Confianza",
      conviction: "Conviccion",
      timeframe: "Marco temporal",
      risk: "Riesgo",
      focus: "Foco",
      queue: "Cola",
      none: "Ninguno",
      never: "Nunca",
      shown: "mostrados",
      auto: "auto",
      coinsUnit: "criptos",
      contextFirst: "Contexto primero",
      marketInsightTitle: "Leer el contexto primero",
      marketInsightBody: "Empieza aqui para saber si el entorno ayuda o complica tus decisiones.",
      signalsInsightTitle: "Decidir que merece accion",
      signalsInsightBody: "Esta pantalla sirve para ejecutar, no para recorrer todas las ideas.",
      scannerInsightTitle: "Ordenar que vigilar despues",
      scannerInsightBody: "Usa Scanner cuando quieras una cola de atencion, no mas ruido.",
      alertsInsightTitle: "Volver en el momento correcto",
      alertsInsightBody: "Las alertas protegen tu foco y evitan vigilar el grafico sin parar.",
      profileEyebrow: "Perfil",
      levelBehavior: "Tu nivel cambia el producto, no solo los textos.",
      currentWatchlist: "Lista seguida actual",
      languageField: "Idioma",
      marketField: "Mercado",
      styleField: "Estilo",
      signalsSingle: "Senales de foco unico.",
      signalsGuided: "Senales guiadas.",
      signalsDense: "Senales densas y configurables.",
      helpEyebrow: "Ayuda",
      helpTitle: "Usa el producto en este orden",
      helpCopy: "Lee primero el contexto, luego decide, luego escanea y despues deja que las alertas te hagan volver cuando importe.",
      oneMainSetup: "Un setup principal",
      executionReady: "Setups listos para ejecutar",
      simpleAction: "Accion simple",
      riskInvalidation: "Riesgo e invalidacion",
      threshold: "Umbral",
      deliveryStatus: "Estado de entrega",
      nextReturnWindow: "Proxima ventana de regreso",
      decisionLine: "Linea de decision",
      highPriorityOnly: "Solo prioridad alta",
      returnOnlyOnTrigger: "Volver solo por disparador",
      watchClosest: "Vigila solo lo que esta mas cerca",
      cockpit: "Cockpit",
      sourceLabel: "Fuente",
      updatedLabel: "Actualizado",
      roleLabel: "Rol",
      questionLabel: "Pregunta",
      nextActionLabel: "Accion siguiente",
      visibleCryptoCount: "Cantidad visible de criptos",
      save: "Guardar",
      regime: "Regimen",
      sentiment: "Sentimiento",
      volatility: "Volatilidad",
      focusWindow: "Ventana de foco",
      topSetup: "Setup principal",
      riskPosture: "Postura de riesgo",
      discovery: "Descubrimiento",
      triggerPlan: "Plan de disparo",
      alertReadiness: "Preparacion de alertas",
      threeIdeasMax: "3 ideas maximas",
      modulePending: "es el siguiente modulo por conectar.",
    },
  },
};

const state = {
  config: null,
  market: null,
  signals: null,
  alerts: null,
  scanner: null,
  user: null,
  view: null,
  loading: true,
  error: "",
};

window.onTelegramAuth = async function onTelegramAuth(telegramUser) {
  state.loading = true;
  state.error = "";
  render();

  try {
    state.user = await apiRequest("/auth/telegram", {
      method: "POST",
      body: JSON.stringify(telegramUser),
    });
    state.view = null;
  } catch (error) {
    state.error = extractErrorMessage(error);
  } finally {
    state.loading = false;
    render();
  }
};

function getText() {
  const language = state.user?.language || "en";
  return copy[language] || copy.en;
}

function valueLabel(group, key) {
  const text = getText();
  if (!key) {
    return text.labels.unset;
  }
  return text.values[group]?.[key] || text.labels.unset;
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
      ["Keep only high-priority alerts active.", "Garde seulement les alertes de haute priorite actives."],
      ["Let alerts bring you back when the trigger gets close.", "Laisse les alertes te faire revenir quand le trigger se rapproche."],
      ["Use one clear action, not constant monitoring.", "Garde une action claire, pas une surveillance constante."],
      ["Keep clean high and medium alerts active, not everything.", "Garde les alertes propres en haute et moyenne priorite, pas toutes."],
      ["Use trigger distance to decide when to look again.", "Utilise la distance au trigger pour savoir quand revenir regarder."],
      ["Let alerts support decisions instead of adding noise.", "Laisse les alertes soutenir la decision au lieu d'ajouter du bruit."],
      ["Alerts are suggestions for what to watch next, not auto-execution.", "Les alertes sont des suggestions sur quoi surveiller ensuite, pas une execution automatique."],
      ["Keep only the cleanest high-priority ideas active to avoid noise.", "Garde seulement les idees de haute priorite les plus propres pour eviter le bruit."],
      ["Review the chart when the trigger is close instead of monitoring constantly.", "Reviens sur le graphique quand le trigger est proche au lieu de surveiller sans arret."],
      ["Keep only a few ideas in view.", "Garde seulement quelques idees dans le champ."],
      ["Watch the trigger, not every candle.", "Observe le trigger, pas chaque bougie."],
      ["Let alerts bring the market back to you.", "Laisse les alertes ramener le marche a toi."],
      ["Start with the hottest names before building names.", "Commence par les noms les plus chauds avant les noms en construction."],
      ["Use trigger plans to guide attention and timing.", "Utilise les plans de trigger pour guider l'attention et le timing."],
      ["Keep alerts armed so Scanner stays focused.", "Garde les alertes armees pour que le Scanner reste focalise."],
      ["Start with Hot names before spending attention on Building ones.", "Commence par les noms chauds avant de depenser ton attention sur ceux en construction."],
      ["Use the trigger plan to decide if the setup is alive, not just interesting.", "Utilise le plan de trigger pour voir si le setup est vivant, pas seulement interessant."],
      ["Keep alerts armed so Scanner can reduce chart babysitting.", "Garde les alertes armees pour que le Scanner reduise la surveillance du graphique."],
      ["Start with Hot names and let Building names wait their turn.", "Commence par les noms chauds et laisse les noms en construction attendre leur tour."],
      ["If the trigger is not clean, keep the idea in Scanner instead of forcing a trade.", "Si le trigger n'est pas propre, laisse l'idee dans le Scanner au lieu de forcer un trade."],
      ["Use alerts to protect attention and re-check the chart only when Scanner gets closer.", "Utilise les alertes pour proteger ton attention et ne reviens sur le chart que lorsque le Scanner se rapproche."],
      ["Alert on breakout confirmation, then execute only if follow-through holds.", "Alerte sur confirmation de cassure, puis execute seulement si le mouvement tient."],
      ["Let the alert bring the pair back to you instead of front-running the move.", "Laisse l'alerte ramener la paire a toi au lieu d'anticiper le mouvement."],
      ["Keep it on alerts only and skip active risk until the structure resets.", "Garde cette idee en alertes seulement et evite le risque actif tant que la structure ne se remet pas en place."],
      ["High velocity. Cut size and avoid chasing extension candles.", "Vitesse elevee. Reduis la taille et evite de chasser les bougies d'extension."],
      ["Moderate volatility. Wait for confirmation before committing full size.", "Volatilite moderee. Attends la confirmation avant de prendre la taille complete."],
      ["Controlled conditions. Favor clean structure over speed.", "Conditions controlees. Favorise une structure propre plutot que la vitesse."],
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
      ["Structure is active, but trigger quality still needs a cleaner confirmation.", "La estructura esta activa, pero la calidad del disparador todavia necesita una confirmacion mas limpia."],
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
      ["Keep only high-priority alerts active.", "Manten activas solo las alertas de prioridad alta."],
      ["Let alerts bring you back when the trigger gets close.", "Deja que las alertas te hagan volver cuando el trigger se acerque."],
      ["Use one clear action, not constant monitoring.", "Usa una accion clara, no monitoreo constante."],
      ["Keep clean high and medium alerts active, not everything.", "Manten activas solo las alertas limpias de prioridad alta y media, no todas."],
      ["Use trigger distance to decide when to look again.", "Usa la distancia al trigger para decidir cuando volver a mirar."],
      ["Let alerts support decisions instead of adding noise.", "Deja que las alertas apoyen la decision en lugar de agregar ruido."],
      ["Alerts are suggestions for what to watch next, not auto-execution.", "Las alertas son sugerencias sobre que vigilar despues, no autoejecucion."],
      ["Keep only the cleanest high-priority ideas active to avoid noise.", "Manten activas solo las ideas de prioridad alta mas limpias para evitar ruido."],
      ["Review the chart when the trigger is close instead of monitoring constantly.", "Revisa el grafico cuando el trigger este cerca en lugar de vigilar constantemente."],
      ["Keep only a few ideas in view.", "Manten solo unas pocas ideas a la vista."],
      ["Watch the trigger, not every candle.", "Mira el trigger, no cada vela."],
      ["Let alerts bring the market back to you.", "Deja que las alertas devuelvan el mercado a tu pantalla."],
      ["Start with the hottest names before building names.", "Empieza por los nombres mas calientes antes que los que estan construyendose."],
      ["Use trigger plans to guide attention and timing.", "Usa planes de trigger para guiar la atencion y el timing."],
      ["Keep alerts armed so Scanner stays focused.", "Mantén las alertas activas para que Scanner siga enfocado."],
      ["Start with Hot names before spending attention on Building ones.", "Empieza por los nombres calientes antes de gastar atencion en los que se estan construyendo."],
      ["Use the trigger plan to decide if the setup is alive, not just interesting.", "Usa el plan de trigger para decidir si el setup sigue vivo, no solo interesante."],
      ["Keep alerts armed so Scanner can reduce chart babysitting.", "Mantén las alertas activas para que Scanner reduzca la vigilancia constante del grafico."],
      ["Start with Hot names and let Building names wait their turn.", "Empieza por los nombres calientes y deja que los que se construyen esperen su turno."],
      ["If the trigger is not clean, keep the idea in Scanner instead of forcing a trade.", "Si el trigger no es limpio, deja la idea en Scanner en lugar de forzar un trade."],
      ["Use alerts to protect attention and re-check the chart only when Scanner gets closer.", "Usa alertas para proteger la atencion y revisa el grafico solo cuando el Scanner se acerque."],
      ["Alert on breakout confirmation, then execute only if follow-through holds.", "Alerta en confirmacion de ruptura y ejecuta solo si el movimiento se sostiene."],
      ["Let the alert bring the pair back to you instead of front-running the move.", "Deja que la alerta devuelva el par a tu pantalla en lugar de anticipar el movimiento."],
      ["Keep it on alerts only and skip active risk until the structure resets.", "Dejalo solo en alertas y evita riesgo activo hasta que la estructura se reinicie."],
      ["High velocity. Cut size and avoid chasing extension candles.", "Velocidad alta. Reduce tamano y evita perseguir velas de extension."],
      ["Moderate volatility. Wait for confirmation before committing full size.", "Volatilidad moderada. Espera confirmacion antes de usar tamano completo."],
      ["Controlled conditions. Favor clean structure over speed.", "Condiciones controladas. Prioriza estructura limpia sobre velocidad."],
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

function localizeTerm(value) {
  const locale = getText().locale;
  if (!locale || !LOCALIZED_TERMS[locale]) {
    return value;
  }
  return LOCALIZED_TERMS[locale].statuses[value] || value;
}

function localizeText(value) {
  if (!value) {
    return value;
  }
  const locale = getText().locale;
  if (!locale || !LOCALIZED_TERMS[locale]) {
    return value;
  }
  return LOCALIZED_TERMS[locale].replacements.reduce((output, [from, to]) => output.split(from).join(to), value);
}

function getUserLevel(user = state.user) {
  const level = user?.level;
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

function formatScannerLimitValue(user) {
  const text = getText();
  const level = getUserLevel(user);
  const effective = getEffectiveScannerLimit(user);
  if (level === "beginner" || level === "medium") {
    return `${effective} ${text.ui.auto}`;
  }
  return `${effective} ${text.ui.coinsUnit}`;
}

function getEffectiveAlertsPriority(user = state.user) {
  const level = getUserLevel(user);
  if (level === "beginner") {
    return "high";
  }
  if (level === "medium") {
    return "medium";
  }
  return user?.alerts_min_priority || "high";
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const body = await response.text();
    const error = new Error(body || `Request failed with status ${response.status}`);
    error.status = response.status;
    throw error;
  }

  return response.json();
}

async function loadConfig() {
  state.config = await apiRequest("/web/config");
}

async function loadCurrentUser() {
  try {
    state.user = await apiRequest("/web/me");
  } catch (error) {
    if (error.status === 401) {
      state.user = null;
      return;
    }
    throw error;
  }
}

async function patchCurrentUser(patch) {
  state.loading = true;
  state.error = "";
  render();

  try {
    state.user = await apiRequest("/web/me", {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
  } catch (error) {
    state.error = extractErrorMessage(error);
  } finally {
    state.loading = false;
    render();
  }
}

async function loadMarket() {
  state.market = await apiRequest("/web/market");
}

async function loadSignals() {
  state.signals = await apiRequest("/web/signals");
}

async function loadAlerts() {
  state.alerts = await apiRequest("/web/alerts");
}

async function loadScanner() {
  state.scanner = await apiRequest("/web/scanner");
}

async function resetCurrentUser() {
  state.loading = true;
  state.error = "";
  render();

  try {
    state.user = await apiRequest("/web/me/reset", { method: "POST" });
    state.view = null;
  } catch (error) {
    state.error = extractErrorMessage(error);
  } finally {
    state.loading = false;
    render();
  }
}

async function logout() {
  state.loading = true;
  state.error = "";
  render();

  try {
    await apiRequest("/auth/logout", { method: "POST" });
    state.user = null;
    state.view = null;
  } catch (error) {
    state.error = extractErrorMessage(error);
  } finally {
    state.loading = false;
    render();
  }
}

function extractErrorMessage(error) {
  try {
    const parsed = JSON.parse(error.message);
    if (parsed.detail) {
      return parsed.detail;
    }
  } catch (parsingError) {
    return error.message;
  }
  return error.message;
}

function formatMarketPrice(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }

  const maximumFractionDigits = value >= 1000 ? 2 : value >= 1 ? 2 : 6;
  return `$${value.toLocaleString(undefined, { maximumFractionDigits })}`;
}

function formatMarketPercent(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }

  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)}%`;
}

function formatMarketVolume(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }

  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function formatMarketProvider(value) {
  if (!value) {
    return null;
  }

  if (value === "coingecko") {
    return "CoinGecko";
  }

  if (value === "coinbase") {
    return "Coinbase";
  }

  if (value === "binance") {
    return "Binance";
  }

  return value;
}

function formatMarketUpdatedAt(value) {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDeliveryStatus(value) {
  const text = getText();
  if (value === "cooldown") {
    return text.alerts.cooldown;
  }
  if (value === "armed") {
    return text.alerts.armed;
  }
  if (value === "off") {
    return text.alerts.disarmed;
  }
  return text.alerts.quiet;
}

function getTradingViewSymbol(symbol) {
  return TRADINGVIEW_SYMBOL_MAP[symbol] || TRADINGVIEW_SYMBOL_MAP.BTC;
}

function getTradingViewLocale() {
  const language = state.user?.language || "en";
  return language === "fr" || language === "es" ? language : "en";
}

function getTradingViewInterval() {
  return state.user?.trading_style === "scalping" ? "15" : "60";
}

function buildTradingViewLink(symbol) {
  const tradingViewSymbol = getTradingViewSymbol(symbol);
  const [exchange, pair] = tradingViewSymbol.split(":");
  return `https://www.tradingview.com/symbols/${exchange}-${pair}/`;
}

function renderTradingViewPanel({ symbol, title, watchlist }) {
  const text = getText();
  const activeSymbol = symbol || "BTC";
  return `
    <section class="tv-card">
      <div class="screen-head">
        <div>
          <p class="eyebrow">${escapeHtml(text.ui.chartEyebrow)}</p>
          <h2 class="screen-title">${escapeHtml(title)}</h2>
        </div>
        <span class="setup-badge">${escapeHtml(activeSymbol)}</span>
      </div>
      <div
        class="tradingview-widget-container tv-embed"
        data-tradingview-symbol="${escapeHtml(activeSymbol)}"
        data-tradingview-watchlist="${escapeHtml(JSON.stringify(watchlist || []))}"
      >
        <div class="tradingview-widget-container__widget"></div>
      </div>
    </section>
  `;
}

function renderHeader() {
  if (!state.user) {
    sessionButton.textContent = "Session";
    return;
  }

  const text = getText();
  sessionButton.textContent = text.authLogout;
}

function shell(content) {
  const errorMarkup = state.error
    ? `<p class="status-note error-note">${escapeHtml(state.error)}</p>`
    : '<p class="status-note"></p>';
  return `${errorMarkup}${content}`;
}

function renderLoading() {
  return shell(`<section class="loading-card"><p class="screen-copy">${escapeHtml(getText().loading)}</p></section>`);
}

function renderAuthCard() {
  const text = getText();
  const isEnabled = Boolean(state.config?.telegram_login_enabled);

  return shell(`
    <section class="hero-card">
      <img class="hero-media" src="/assets/logo.svg" alt="ScannerHT logo" />
      <p class="eyebrow">${escapeHtml(text.authEyebrow)}</p>
      <h2 class="hero-title">${escapeHtml(text.authTitle)}</h2>
      <p class="hero-copy">${escapeHtml(text.authCopy)}</p>
      <div class="screen-card auth-widget-card">
        <div id="telegram-login-slot"></div>
        <p class="helper-text">${escapeHtml(isEnabled ? text.authHint : text.authUnavailable)}</p>
      </div>
    </section>
  `);
}

function renderAccountCard() {
  const text = getText();
  const level = valueLabel("level", state.user.level);
  const scanner = formatScannerLimitValue(state.user);
  return `
    <section class="profile-card">
      <p class="eyebrow">${escapeHtml(text.labels.account)}</p>
      <div class="summary-row">
        <span class="summary-label">${escapeHtml(text.authStatus)}</span>
        <span class="summary-value">#${state.user.user_id}</span>
      </div>
      <div class="summary-row">
        <span class="summary-label">${escapeHtml(text.labels.level)}</span>
        <span class="summary-value">${escapeHtml(level)}</span>
      </div>
      <div class="summary-row">
        <span class="summary-label">${escapeHtml(text.labels.scannerLimit)}</span>
        <span class="summary-value">${escapeHtml(scanner)}</span>
      </div>
    </section>
  `;
}

function getMenuAction(key) {
  if (key === "settings") {
    return "open-settings";
  }
  if (key === "market") {
    return "open-market";
  }
  if (key === "signals") {
    return "open-signals";
  }
  if (key === "alerts") {
    return "open-alerts";
  }
  if (key === "scanner") {
    return "open-scanner";
  }
  if (key === "help") {
    return "open-help";
  }
  return "placeholder";
}

function renderIdentityStrip() {
  const text = getText();
  const user = state.user;
  return `
    <div class="identity-strip">
      <div class="identity-pill">
        <span class="identity-label">${escapeHtml(text.labels.level)}</span>
        <strong>${escapeHtml(valueLabel("level", user.level))}</strong>
      </div>
      <div class="identity-pill">
        <span class="identity-label">${escapeHtml(text.labels.market)}</span>
        <strong>${escapeHtml(valueLabel("market", user.market))}</strong>
      </div>
      <div class="identity-pill">
        <span class="identity-label">${escapeHtml(text.labels.style)}</span>
        <strong>${escapeHtml(valueLabel("style", user.trading_style))}</strong>
      </div>
      <div class="identity-pill">
        <span class="identity-label">${escapeHtml(text.labels.coins)}</span>
        <strong>${escapeHtml(user.coins.length ? user.coins.join(", ") : text.labels.unset)}</strong>
      </div>
    </div>
  `;
}

function renderInsightBlock({ eyebrow, title, body, items = [] }) {
  return `
    <section class="insight-card">
      <p class="eyebrow">${escapeHtml(eyebrow)}</p>
      <h3 class="insight-title">${escapeHtml(title)}</h3>
      ${body ? `<p class="helper-text">${escapeHtml(body)}</p>` : ""}
      ${
        items.length
          ? `<ul class="insight-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
          : ""
      }
    </section>
  `;
}

function renderChoiceScreen({ badge, title, description, buttons }) {
  const text = getText();
  return shell(`
    ${renderAccountCard()}
    <section class="screen-card">
      <div class="screen-head">
        <div>
          <p class="eyebrow">${escapeHtml(text.ui.setup)}</p>
          <h2 class="screen-title">${escapeHtml(title)}</h2>
        </div>
        <span class="setup-badge">${escapeHtml(badge)}</span>
      </div>
      <p class="screen-copy">${escapeHtml(description)}</p>
      <div class="button-grid">
        ${buttons.join("")}
      </div>
    </section>
  `);
}

function renderScannerLimitScreen() {
  const text = getText();
  const currentValue = getEffectiveScannerLimit(state.user);
  const options = Array.from({ length: COINS.length - 2 }, (_, index) => {
    const value = index + 3;
    return `<option value="${value}" ${value === currentValue ? "selected" : ""}>${value} ${escapeHtml(text.ui.coinsUnit)}</option>`;
  }).join("");

  return shell(`
    ${renderAccountCard()}
    <section class="screen-card">
      <div class="screen-head">
        <div>
          <p class="eyebrow">${escapeHtml(text.settingsTitle)}</p>
          <h2 class="screen-title">${escapeHtml(text.settingsActions.scannerLimit)}</h2>
        </div>
        <span class="setup-badge">Pro</span>
      </div>
      <p class="screen-copy">${escapeHtml(text.ui.scannerCountCopy)}</p>
      <label class="helper-text" for="scanner-limit-select">${escapeHtml(text.ui.visibleCryptoCount)}</label>
      <select id="scanner-limit-select" class="secondary-button">
        ${options}
      </select>
      <div class="screen-actions">
        <button class="primary-button" data-action="scanner-limit-save">${escapeHtml(text.ui.save)}</button>
        <button class="secondary-button" data-action="open-settings">${escapeHtml(text.settingsActions.back)}</button>
      </div>
    </section>
  `);
}

function renderCoinsScreen(settingsMode = false) {
  const text = getText();
  const selectedCoins = Array.isArray(state.user.coins) ? state.user.coins : [];
  const title = settingsMode ? text.settingsActions.coins : text.coinsTitle;
  const badge = settingsMode ? text.settingsTitle : "Setup 4/5";
  const buttons = COINS.map((coin) => {
    const selected = selectedCoins.includes(coin.symbol);
    const action = settingsMode ? "settings-coin" : "coin";
    return `
      <button class="coin-button ${selected ? "is-selected" : ""}" data-action="${action}" data-value="${coin.symbol}">
        ${selected ? "✅ " : ""}${coin.icon} ${coin.symbol}
      </button>
    `;
  }).join("");

  return shell(`
    ${renderAccountCard()}
    <section class="screen-card">
      <div class="screen-head">
        <div>
          <p class="eyebrow">${escapeHtml(badge)}</p>
          <h2 class="screen-title">${escapeHtml(title)}</h2>
        </div>
        <span class="setup-badge">${escapeHtml(`${text.coinsHint}: ${selectedCoins.length}/3`)}</span>
      </div>
      <p class="screen-copy">${escapeHtml(selectedCoins.length ? selectedCoins.join(", ") : "BTC, ETH, SOL...")}</p>
      <div class="coin-grid">${buttons}</div>
      ${settingsMode ? `<div class="screen-actions"><button class="secondary-button" data-action="open-settings">${escapeHtml(text.settingsActions.back)}</button></div>` : ""}
    </section>
  `);
}

function renderSourceMeta({ provider, updatedAt, cached = false, stale = false }) {
  const text = getText();
  if (!provider && !updatedAt) {
    return "";
  }

  return `<div class="market-meta">
    ${provider ? `<span class="helper-text">${escapeHtml(text.ui.sourceLabel)}: ${escapeHtml(provider)}${cached ? " · cached" : ""}${stale ? " · stale" : ""}</span>` : ""}
    ${updatedAt ? `<span class="helper-text">${escapeHtml(text.ui.updatedLabel)}: ${escapeHtml(updatedAt)}</span>` : ""}
  </div>`;
}

function renderDeskLead({ eyebrow, regime, badge, headline, role, question, nextAction, provider, updatedAt, cached, stale }) {
  const text = getText();
  return `
    <section class="screen-card">
      <div class="screen-head">
        <div>
          <p class="eyebrow">${escapeHtml(eyebrow)}</p>
          <h2 class="screen-title">${escapeHtml(localizeText(regime))}</h2>
        </div>
        <span class="setup-badge">${escapeHtml(badge)}</span>
      </div>
      <p class="screen-copy">${escapeHtml(localizeText(headline))}</p>
      <div class="desk-meta-grid">
        <article class="desk-meta-card">
          <span class="stat-label">${escapeHtml(text.ui.roleLabel)}</span>
          <strong>${escapeHtml(role)}</strong>
        </article>
        <article class="desk-meta-card">
          <span class="stat-label">${escapeHtml(text.ui.questionLabel)}</span>
          <strong>${escapeHtml(question)}</strong>
        </article>
        ${
          nextAction
            ? `<article class="desk-meta-card">
                <span class="stat-label">${escapeHtml(text.ui.nextActionLabel)}</span>
                <strong>${escapeHtml(localizeText(nextAction))}</strong>
              </article>`
            : ""
        }
      </div>
      ${renderSourceMeta({ provider, updatedAt, cached, stale })}
    </section>
  `;
}

function renderStatCards(cards) {
  return `
    <div class="market-summary">
      ${cards
        .map(
          (card) => `
            <article class="market-card ${escapeHtml(card.tone ? toneClass("tone", card.tone) : "")}">
              <span class="stat-label">${escapeHtml(card.label)}</span>
              <strong>${escapeHtml(String(card.value))}</strong>
              <span class="helper-text">${escapeHtml(card.hint)}</span>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderDeskNotes(title, items, backLabel) {
  return `
    <section class="market-checklist">
      <p class="eyebrow">${escapeHtml(title)}</p>
      <ul>
        ${items.map((item) => `<li>${escapeHtml(localizeText(item))}</li>`).join("")}
      </ul>
      <div class="screen-actions">
        <button class="secondary-button" data-action="back-main">${escapeHtml(backLabel)}</button>
      </div>
    </section>
  `;
}

function slugifyTone(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function toneClass(prefix, value) {
  const slug = slugifyTone(value);
  return slug ? `${prefix}-${slug}` : "";
}

function renderSignalCard(setup, level, text) {
  const conviction = localizeTerm(setup.conviction);
  const direction = localizeText(setup.direction);
  const trigger = localizeText(setup.entry_trigger);
  const size = localizeText(setup.size_plan);
  const invalidation = localizeText(setup.invalidation);
  const entryPlan = localizeText(setup.entry_plan);
  const risk = localizeText(setup.risk_note);
  const why = localizeText(setup.why_this_signal);
  const confidenceExplanation = localizeText(setup.confidence_explanation);
  const contextNote = localizeText(setup.context_note);
  const status = localizeTerm(setup.status);
  const cardTone = toneClass("tone", setup.status);
  const signalTone = level === "beginner" ? toneClass("tone", setup.conviction) : toneClass("tone", setup.status);
  if (level === "beginner") {
    return `
      <article class="asset-card asset-card--signal ${escapeHtml(cardTone)}">
        <div class="asset-head">
          <div class="asset-symbol">${escapeHtml(setup.symbol)}</div>
          <span class="asset-signal ${escapeHtml(signalTone)}">${escapeHtml(conviction)}</span>
        </div>
        <p class="helper-text">${escapeHtml(text.ui.trigger)}: ${escapeHtml(trigger)}</p>
        <p class="helper-text">${escapeHtml(why)}</p>
      </article>
    `;
  }

  if (level === "medium") {
    return `
      <article class="asset-card asset-card--signal ${escapeHtml(cardTone)}">
        <div class="asset-head">
          <div class="asset-symbol">${escapeHtml(setup.symbol)}</div>
          <span class="asset-signal ${escapeHtml(signalTone)}">${escapeHtml(status)}</span>
        </div>
        <p class="helper-text">${escapeHtml(text.ui.action)}: ${escapeHtml(direction)} · ${escapeHtml(conviction)}</p>
        ${formatMarketPrice(setup.last_price) ? `<div class="score-row"><span>${escapeHtml(text.ui.price)}</span><strong>${escapeHtml(formatMarketPrice(setup.last_price))}</strong></div>` : ""}
        <p class="helper-text">${escapeHtml(text.ui.trigger)}: ${escapeHtml(trigger)}</p>
        <p class="helper-text">${escapeHtml(text.ui.size)}: ${escapeHtml(size)}</p>
        <p class="helper-text">${escapeHtml(why)}</p>
        <p class="helper-text">${escapeHtml(risk)}</p>
        <p class="helper-text">${escapeHtml(text.scanner.invalidation)}: ${escapeHtml(invalidation)}</p>
      </article>
    `;
  }

  return `
    <article class="asset-card asset-card--signal ${escapeHtml(cardTone)}">
      <div class="asset-head">
        <div class="asset-symbol">${escapeHtml(setup.symbol)}</div>
        <span class="asset-signal ${escapeHtml(signalTone)}">${escapeHtml(status)}</span>
      </div>
      <p class="helper-text">${escapeHtml(direction)}</p>
      ${formatMarketPrice(setup.last_price) ? `<div class="score-row"><span>${escapeHtml(text.ui.price)}</span><strong>${escapeHtml(formatMarketPrice(setup.last_price))}</strong></div>` : ""}
      ${formatMarketPercent(setup.price_change_percent) ? `<div class="score-row"><span>24h</span><strong>${escapeHtml(formatMarketPercent(setup.price_change_percent))}</strong></div>` : ""}
      <div class="score-row"><span>${escapeHtml(text.ui.confidence)}</span><strong>${setup.confidence}</strong></div>
      <div class="score-row"><span>${escapeHtml(text.ui.conviction)}</span><strong>${escapeHtml(conviction)}</strong></div>
      <div class="score-row"><span>${escapeHtml(text.ui.timeframe)}</span><strong>${escapeHtml(setup.timeframe)}</strong></div>
      <p class="helper-text">${escapeHtml(trigger)}</p>
      <p class="helper-text">${escapeHtml(why)}</p>
      <p class="helper-text">${escapeHtml(confidenceExplanation)}</p>
      <p class="helper-text">${escapeHtml(entryPlan)}</p>
      <p class="helper-text">${escapeHtml(contextNote)}</p>
      <p class="helper-text">${escapeHtml(size)}</p>
      <p class="helper-text">${escapeHtml(text.scanner.invalidation)}: ${escapeHtml(invalidation)}</p>
      <p class="helper-text">${escapeHtml(risk)}</p>
    </article>
  `;
}

function renderAlertCard(item, level) {
  const text = getText();
  const priority = localizeTerm(item.priority);
  const alertType = localizeText(item.alert_type);
  const direction = localizeText(item.direction);
  const thesis = localizeText(item.thesis);
  const actionNote = localizeText(item.action_note);
  const why = localizeText(item.why_this_signal);
  const confidenceExplanation = localizeText(item.confidence_explanation);
  const contextNote = localizeText(item.context_note);
  const risk = localizeText(item.risk_note);
  const invalidation = localizeText(item.invalidation);
  const alertTone = toneClass("tone", item.priority);
  if (level === "beginner") {
    return `
      <article class="asset-card asset-card--alert ${escapeHtml(alertTone)}">
        <div class="asset-head">
          <div class="asset-symbol">${escapeHtml(item.symbol)}</div>
          <span class="asset-signal ${escapeHtml(alertTone)}">${escapeHtml(priority)}</span>
        </div>
        ${formatMarketPrice(item.trigger_price) ? `<div class="score-row"><span>${escapeHtml(text.ui.trigger)}</span><strong>${escapeHtml(formatMarketPrice(item.trigger_price))}</strong></div>` : ""}
        <p class="helper-text">${escapeHtml(actionNote)}</p>
        <p class="helper-text">${escapeHtml(why)}</p>
      </article>
    `;
  }

  if (level === "medium") {
    return `
      <article class="asset-card asset-card--alert ${escapeHtml(alertTone)}">
        <div class="asset-head">
          <div class="asset-symbol">${escapeHtml(item.symbol)}</div>
          <span class="asset-signal ${escapeHtml(alertTone)}">${escapeHtml(priority)}</span>
        </div>
        <p class="helper-text">${escapeHtml(alertType)} · ${escapeHtml(direction)}</p>
        ${formatMarketPrice(item.trigger_price) ? `<div class="score-row"><span>${escapeHtml(text.ui.trigger)}</span><strong>${escapeHtml(formatMarketPrice(item.trigger_price))}</strong></div>` : ""}
        ${formatMarketPercent(item.distance_percent) ? `<div class="score-row"><span>${escapeHtml(text.ui.distance)}</span><strong>${escapeHtml(formatMarketPercent(item.distance_percent))}</strong></div>` : ""}
        <p class="helper-text">${escapeHtml(why)}</p>
        <p class="helper-text">${escapeHtml(risk)}</p>
        <p class="helper-text">${escapeHtml(text.scanner.invalidation)}: ${escapeHtml(invalidation)}</p>
      </article>
    `;
  }

  return `
    <article class="asset-card asset-card--alert ${escapeHtml(alertTone)}">
      <div class="asset-head">
        <div class="asset-symbol">${escapeHtml(item.symbol)}</div>
        <span class="asset-signal ${escapeHtml(alertTone)}">${escapeHtml(priority)}</span>
      </div>
      <p class="helper-text">${escapeHtml(alertType)} · ${escapeHtml(direction)}</p>
      ${formatMarketPrice(item.last_price) ? `<div class="score-row"><span>${escapeHtml(text.ui.price)}</span><strong>${escapeHtml(formatMarketPrice(item.last_price))}</strong></div>` : ""}
      ${formatMarketPrice(item.trigger_price) ? `<div class="score-row"><span>${escapeHtml(text.ui.trigger)}</span><strong>${escapeHtml(formatMarketPrice(item.trigger_price))}</strong></div>` : ""}
      ${formatMarketPercent(item.distance_percent) ? `<div class="score-row"><span>${escapeHtml(text.ui.distance)}</span><strong>${escapeHtml(formatMarketPercent(item.distance_percent))}</strong></div>` : ""}
      ${formatMarketPercent(item.price_change_percent) ? `<div class="score-row"><span>24h</span><strong>${escapeHtml(formatMarketPercent(item.price_change_percent))}</strong></div>` : ""}
      <p class="helper-text">${escapeHtml(thesis)}</p>
      <p class="helper-text">${escapeHtml(why)}</p>
      <p class="helper-text">${escapeHtml(confidenceExplanation)}</p>
      <p class="helper-text">${escapeHtml(contextNote)}</p>
      <p class="helper-text">${escapeHtml(actionNote)}</p>
      <p class="helper-text">${escapeHtml(text.scanner.invalidation)}: ${escapeHtml(invalidation)}</p>
      <p class="helper-text">${escapeHtml(risk)}</p>
    </article>
  `;
}

function renderScannerCard(candidate, level, text) {
  const status = localizeTerm(candidate.status);
  const urgency = localizeTerm(candidate.urgency);
  const pattern = localizeText(candidate.pattern);
  const triggerPlan = localizeText(candidate.trigger_plan);
  const catalyst = localizeText(candidate.catalyst);
  const invalidation = localizeText(candidate.invalidation);
  const why = localizeText(candidate.why_this_signal);
  const confidenceExplanation = localizeText(candidate.confidence_explanation);
  const contextNote = localizeText(candidate.context_note);
  const risk = localizeText(candidate.risk_note);
  const scannerTone = toneClass("tone", candidate.status);
  if (level === "beginner") {
    return `
      <article class="asset-card asset-card--scanner ${escapeHtml(scannerTone)}">
        <div class="asset-head">
          <div class="asset-symbol">${escapeHtml(candidate.symbol)}</div>
          <span class="asset-signal ${escapeHtml(scannerTone)}">${escapeHtml(status)}</span>
        </div>
        <p class="helper-text">${escapeHtml(text.scanner.trigger)}: ${escapeHtml(triggerPlan)}</p>
        <p class="helper-text">${escapeHtml(why)}</p>
      </article>
    `;
  }

  if (level === "medium") {
    return `
      <article class="asset-card asset-card--scanner ${escapeHtml(scannerTone)}">
        <div class="asset-head">
          <div class="asset-symbol">${escapeHtml(`#${candidate.rank} ${candidate.symbol}`)}</div>
          <span class="asset-signal ${escapeHtml(scannerTone)}">${escapeHtml(status)}</span>
        </div>
        <p class="helper-text">${escapeHtml(pattern)}</p>
        ${formatMarketPrice(candidate.last_price) ? `<div class="score-row"><span>${escapeHtml(text.ui.price)}</span><strong>${escapeHtml(formatMarketPrice(candidate.last_price))}</strong></div>` : ""}
        <div class="score-row"><span>${escapeHtml(text.scanner.urgency)}</span><strong>${escapeHtml(urgency)}</strong></div>
        <div class="score-row"><span>${escapeHtml(text.scanner.alerts)}</span><strong>${escapeHtml(candidate.alert_ready ? text.scanner.armed : text.scanner.off)}</strong></div>
        <p class="helper-text">${escapeHtml(text.scanner.trigger)}: ${escapeHtml(triggerPlan)}</p>
        <p class="helper-text">${escapeHtml(why)}</p>
        <p class="helper-text">${escapeHtml(risk)}</p>
      </article>
    `;
  }

  return `
    <article class="asset-card asset-card--scanner ${escapeHtml(scannerTone)}">
      <div class="asset-head">
        <div class="asset-symbol">${escapeHtml(`#${candidate.rank} ${candidate.symbol}`)}</div>
        <span class="asset-signal ${escapeHtml(scannerTone)}">${escapeHtml(status)}</span>
      </div>
      <p class="helper-text">${escapeHtml(pattern)}</p>
      ${formatMarketPrice(candidate.last_price) ? `<div class="score-row"><span>${escapeHtml(text.ui.price)}</span><strong>${escapeHtml(formatMarketPrice(candidate.last_price))}</strong></div>` : ""}
      ${formatMarketPercent(candidate.price_change_percent) ? `<div class="score-row"><span>24h</span><strong>${escapeHtml(formatMarketPercent(candidate.price_change_percent))}</strong></div>` : ""}
      <div class="score-row"><span>${escapeHtml(text.ui.origin)}</span><strong>${escapeHtml(candidate.watchlist_match ? text.scanner.selected : text.scanner.discovery)}</strong></div>
      <div class="score-row"><span>${escapeHtml(text.scanner.score)}</span><strong>${candidate.scanner_score}</strong></div>
      <div class="score-row"><span>${escapeHtml(text.scanner.urgency)}</span><strong>${escapeHtml(urgency)}</strong></div>
      <div class="score-row"><span>${escapeHtml(text.scanner.alerts)}</span><strong>${escapeHtml(candidate.alert_ready ? text.scanner.armed : text.scanner.off)}</strong></div>
      <p class="helper-text">${escapeHtml(catalyst)}</p>
      <p class="helper-text">${escapeHtml(why)}</p>
      <p class="helper-text">${escapeHtml(confidenceExplanation)}</p>
      <p class="helper-text">${escapeHtml(contextNote)}</p>
      <p class="helper-text">${escapeHtml(triggerPlan)}</p>
      <p class="helper-text">${escapeHtml(text.scanner.invalidation)}: ${escapeHtml(invalidation)}</p>
      <p class="helper-text">${escapeHtml(risk)}</p>
    </article>
  `;
}

function renderMarket() {
  const text = getText();
  const market = state.market;
  const marketProvider = formatMarketProvider(market.data_provider);
  const marketUpdatedAt = formatMarketUpdatedAt(market.data_updated_at);
  const chartSymbol = market.assets?.[0]?.symbol || "BTC";
  const chartWatchlist = (market.assets || []).map((asset) => asset.symbol);
  const desk = text.desks.market;
  return shell(`
    ${renderAccountCard()}
    ${renderDeskLead({
      eyebrow: desk.eyebrow,
      regime: market.regime,
      badge: market.data_mode,
      headline: localizeText(market.outlook_headline),
      role: desk.role,
      question: desk.question,
      provider: marketProvider,
      updatedAt: marketUpdatedAt,
      cached: market.data_cached,
      stale: market.data_stale,
    })}

    ${renderStatCards([
      { label: text.ui.sentiment, value: `${market.sentiment_score}/100`, hint: market.market_type, tone: market.regime },
      { label: text.ui.volatility, value: localizeText(market.volatility_label), hint: market.trading_style, tone: market.volatility_label },
      { label: text.ui.focus, value: localizeText(market.focus_window), hint: text.ui.contextFirst, tone: market.focus_window },
    ])}

    ${renderTradingViewPanel({
      symbol: chartSymbol,
      title: desk.chartTitle,
      watchlist: chartWatchlist,
    })}

    <section class="market-assets">
      ${market.assets
        .map(
          (asset) => `
            <article class="asset-card asset-card--market ${escapeHtml(toneClass("tone", asset.signal))}">
              <div class="asset-head">
                <div class="asset-symbol">${escapeHtml(asset.symbol)}</div>
                <span class="asset-signal ${escapeHtml(toneClass("tone", asset.signal))}">${escapeHtml(localizeText(asset.signal))}</span>
              </div>
              <p class="helper-text">${escapeHtml(localizeText(asset.setup))}</p>
              ${formatMarketPrice(asset.last_price) ? `<div class="score-row"><span>${escapeHtml(text.ui.price)}</span><strong>${escapeHtml(formatMarketPrice(asset.last_price))}</strong></div>` : ""}
              ${formatMarketPercent(asset.price_change_percent) ? `<div class="score-row"><span>24h</span><strong>${escapeHtml(formatMarketPercent(asset.price_change_percent))}</strong></div>` : ""}
              ${formatMarketVolume(asset.quote_volume) ? `<div class="score-row"><span>${escapeHtml(text.ui.volume)}</span><strong>${escapeHtml(formatMarketVolume(asset.quote_volume))}</strong></div>` : ""}
              <div class="score-row"><span>Pulse</span><strong>${asset.pulse_score}</strong></div>
              <div class="score-row"><span>Breakout</span><strong>${asset.breakout_score}</strong></div>
              <div class="score-row"><span>Volatility</span><strong>${asset.volatility_score}</strong></div>
              <div class="score-row"><span>Bias</span><strong>${escapeHtml(localizeText(asset.bias))}</strong></div>
            </article>
          `,
        )
        .join("")}
    </section>

    ${renderDeskNotes(desk.noteTitle, market.checklist, text.settingsActions.back)}
  `);
}

function renderSignals() {
  const text = getText();
  const signals = state.signals;
  const level = getUserLevel(state.user);
  const marketProvider = formatMarketProvider(signals.data_provider);
  const marketUpdatedAt = formatMarketUpdatedAt(signals.data_updated_at);
  const chartSymbol = signals.top_symbol || signals.setups?.[0]?.symbol || "BTC";
  const chartWatchlist = (signals.setups || []).map((setup) => setup.symbol);
  const desk = text.desks.signals;
  const topSetup = signals.setups?.[0];
  const statCards =
    level === "beginner"
      ? [
          { label: text.ui.topFocus, value: signals.top_symbol || text.ui.none, hint: signals.market_type, tone: topSetup?.status },
          { label: text.ui.conviction, value: topSetup?.conviction ? localizeTerm(topSetup.conviction) : text.ui.none, hint: signals.trading_style, tone: topSetup?.conviction },
          { label: text.ui.action, value: signals.next_action || text.ui.none, hint: text.ui.oneMainSetup, tone: topSetup?.status },
        ]
      : level === "medium"
        ? [
            { label: text.ui.topFocus, value: signals.top_symbol || text.ui.none, hint: signals.market_type, tone: topSetup?.status },
            { label: text.ui.conviction, value: topSetup?.conviction ? localizeTerm(topSetup.conviction) : text.ui.none, hint: topSetup?.status ? localizeTerm(topSetup.status) : signals.trading_style, tone: topSetup?.conviction },
            { label: text.ui.trigger, value: topSetup?.entry_trigger ? localizeText(topSetup.entry_trigger) : text.ui.none, hint: text.ui.decisionLine, tone: topSetup?.status },
            { label: text.ui.size, value: topSetup?.size_plan ? localizeText(topSetup.size_plan) : text.ui.none, hint: localizeText(signals.next_action), tone: topSetup?.status },
          ]
        : [
          { label: "Active", value: signals.ready_count, hint: signals.market_type, tone: "Active" },
          { label: "Watch", value: signals.watch_count, hint: signals.trading_style, tone: "Watch" },
          { label: text.ui.topFocus, value: signals.top_symbol || text.ui.none, hint: signals.execution_bias, tone: topSetup?.status },
          { label: text.ui.risk, value: localizeText(signals.risk_posture), hint: signals.market_type, tone: signals.regime },
        ];
  return shell(`
    ${renderAccountCard()}
    ${renderDeskLead({
      eyebrow: desk.eyebrow,
      regime: signals.regime,
      badge: signals.data_mode,
      headline: localizeText(signals.headline),
      role: desk.role,
      question: desk.question,
      nextAction: localizeText(signals.next_action),
      provider: marketProvider,
      updatedAt: marketUpdatedAt,
      cached: signals.data_cached,
      stale: signals.data_stale,
    })}

    ${renderStatCards(statCards)}

    ${renderTradingViewPanel({
      symbol: chartSymbol,
      title: desk.chartTitle,
      watchlist: chartWatchlist,
    })}

    <section class="market-assets">
      ${signals.setups
        .map((setup) => renderSignalCard(setup, level, text))
        .join("")}
    </section>

    ${renderDeskNotes(desk.noteTitle, signals.checklist, text.settingsActions.back)}
  `);
}

function renderAlerts() {
  const text = getText();
  const alerts = state.alerts;
  const user = state.user;
  const level = getUserLevel(user);
  const effectivePriority = getEffectiveAlertsPriority(user);
  const marketProvider = formatMarketProvider(alerts.data_provider);
  const marketUpdatedAt = formatMarketUpdatedAt(alerts.data_updated_at);
  const chartSymbol = alerts.top_symbol || alerts.items?.[0]?.symbol || "BTC";
  const chartWatchlist = (alerts.items || []).map((item) => item.symbol);
  const desk = text.desks.alerts;
  const topAlert = alerts.items?.[0];
  const summaryRows = [
    `
      <div class="summary-row">
        <span class="summary-label">${escapeHtml(text.alerts.status)}</span>
        <span class="summary-value">${escapeHtml(formatDeliveryStatus(alerts.delivery_status))}</span>
      </div>
    `,
    `
      <div class="summary-row">
        <span class="summary-label">${escapeHtml(text.alerts.priority)}</span>
        <span class="summary-value">${escapeHtml(alerts.delivery_min_priority || text.alerts[effectivePriority])}</span>
      </div>
    `,
  ];

  if (level !== "beginner") {
    summaryRows.push(
      `
        <div class="summary-row">
          <span class="summary-label">${escapeHtml(text.alerts.lastSent)}</span>
          <span class="summary-value">${escapeHtml(formatMarketUpdatedAt(alerts.delivery_last_sent_at) || text.ui.never)}</span>
        </div>
      `,
      `
        <div class="summary-row">
          <span class="summary-label">${escapeHtml(text.alerts.nextWindow)}</span>
          <span class="summary-value">${escapeHtml(formatMarketUpdatedAt(alerts.delivery_next_eligible_at) || text.alerts.quiet)}</span>
        </div>
      `,
    );
  }
  const alertStatCards =
    level === "beginner"
      ? [
          { label: text.ui.topFocus, value: alerts.top_symbol || text.ui.none, hint: text.ui.highPriorityOnly, tone: topAlert?.priority },
          { label: text.alerts.status, value: formatDeliveryStatus(alerts.delivery_status), hint: alerts.next_action, tone: alerts.delivery_status },
          { label: text.alerts.priority, value: alerts.delivery_min_priority || text.alerts[effectivePriority], hint: alerts.active_window, tone: alerts.delivery_min_priority },
        ]
      : level === "medium"
        ? [
            { label: text.ui.topFocus, value: alerts.top_symbol || text.ui.none, hint: alerts.market_type, tone: topAlert?.priority },
            { label: text.ui.trigger, value: formatMarketPrice(topAlert?.trigger_price) || text.ui.none, hint: topAlert?.alert_type ? localizeText(topAlert.alert_type) : alerts.active_window, tone: topAlert?.priority },
            { label: text.ui.distance, value: formatMarketPercent(topAlert?.distance_percent) || text.ui.none, hint: topAlert?.direction ? localizeText(topAlert.direction) : alerts.trading_style, tone: topAlert?.priority },
            { label: text.alerts.priority, value: alerts.delivery_min_priority || text.alerts[effectivePriority], hint: alerts.next_action, tone: alerts.delivery_min_priority },
          ]
        : [
          { label: "High", value: alerts.high_priority_count, hint: alerts.market_type, tone: "High" },
          { label: "Medium", value: alerts.medium_priority_count, hint: alerts.trading_style, tone: "Medium" },
          { label: "Low", value: alerts.low_priority_count, hint: alerts.active_window, tone: "Low" },
          { label: text.ui.topFocus, value: alerts.top_symbol || text.ui.none, hint: text.ui.returnOnlyOnTrigger, tone: topAlert?.priority },
        ];
  return shell(`
    ${renderAccountCard()}
    ${renderDeskLead({
      eyebrow: desk.eyebrow,
      regime: alerts.regime,
      badge: alerts.data_mode,
      headline: localizeText(alerts.headline),
      role: desk.role,
      question: desk.question,
      nextAction: localizeText(alerts.next_action),
      provider: marketProvider,
      updatedAt: marketUpdatedAt,
      cached: alerts.data_cached,
      stale: alerts.data_stale,
    })}

    <section class="screen-card">
      <p class="helper-text">${escapeHtml(localizeText(alerts.delivery_note))}</p>

      <div class="settings-summary">
        ${summaryRows.join("")}
      </div>

      <div class="screen-actions">
        <button
          class="${user.alerts_enabled ? "secondary-button" : "primary-button"}"
          data-action="${user.alerts_enabled ? "alerts-disable" : "alerts-enable"}"
        >
          ${escapeHtml(user.alerts_enabled ? text.alerts.disarm : text.alerts.arm)}
        </button>
      </div>

      ${
        level === "pro"
          ? `<div class="button-grid">
              ${["high", "medium", "low"]
                .map(
                  (priority) => `
                    <button
                      class="coin-button ${effectivePriority === priority ? "is-selected" : ""}"
                      data-action="alerts-priority"
                      data-value="${priority}"
                    >
                      ${escapeHtml(text.alerts[priority])}
                    </button>
                  `,
                )
                .join("")}
            </div>`
          : ""
      }

      ${renderStatCards(alertStatCards)}
    </section>

    ${renderTradingViewPanel({
      symbol: chartSymbol,
      title: desk.chartTitle,
      watchlist: chartWatchlist,
    })}

    <section class="market-assets">
      ${alerts.items
        .map((item) => renderAlertCard(item, level))
        .join("")}
    </section>

    ${renderDeskNotes(
      desk.noteTitle,
      level === "beginner"
        ? [
            "Keep only high-priority alerts active.",
            "Let alerts bring you back when the trigger gets close.",
            "Use one clear action, not constant monitoring.",
          ]
        : level === "medium"
          ? [
              "Keep clean high and medium alerts active, not everything.",
              "Use trigger distance to decide when to look again.",
              "Let alerts support decisions instead of adding noise.",
            ]
          : [
              "Alerts are suggestions for what to watch next, not auto-execution.",
              "Keep only the cleanest high-priority ideas active to avoid noise.",
              "Review the chart when the trigger is close instead of monitoring constantly.",
            ],
      text.settingsActions.back,
    )}
  `);
}

function renderScanner() {
  const text = getText();
  const scanner = state.scanner;
  const level = getUserLevel(state.user);
  const marketProvider = formatMarketProvider(scanner.data_provider);
  const marketUpdatedAt = formatMarketUpdatedAt(scanner.data_updated_at);
  const chartSymbol = scanner.top_symbol || scanner.candidates?.[0]?.symbol || "BTC";
  const chartWatchlist = (scanner.candidates || []).map((candidate) => candidate.symbol);
  const desk = text.desks.scanner;
  const scannerStatCards =
    level === "beginner"
      ? [
          { label: text.ui.topFocus, value: scanner.top_symbol || text.ui.none, hint: text.ui.threeIdeasMax, tone: scanner.candidates?.[0]?.status },
          { label: text.ui.queue, value: scanner.visible_count, hint: scanner.scan_window, tone: scanner.candidates?.[0]?.status },
          { label: text.ui.action, value: scanner.next_action, hint: text.ui.watchClosest, tone: scanner.candidates?.[0]?.status },
        ]
      : level === "medium"
        ? [
            { label: text.scanner.hot, value: scanner.hot_count, hint: scanner.market_type, tone: "Hot" },
            { label: text.scanner.building, value: scanner.building_count, hint: scanner.trading_style, tone: "Building" },
            { label: text.ui.topFocus, value: scanner.top_symbol || text.ui.none, hint: `${scanner.visible_count} ${text.ui.shown}`, tone: scanner.candidates?.[0]?.status },
          ]
        : [
            { label: text.scanner.hot, value: scanner.hot_count, hint: scanner.market_type, tone: "Hot" },
            { label: text.scanner.building, value: scanner.building_count, hint: scanner.trading_style, tone: "Building" },
            { label: text.scanner.early, value: scanner.early_count, hint: scanner.scan_window, tone: "Early" },
            { label: text.ui.topFocus, value: scanner.top_symbol || text.ui.none, hint: `${scanner.visible_count}/${scanner.universe_size} ${text.ui.shown}`, tone: scanner.candidates?.[0]?.status },
          ];

  return shell(`
    ${renderAccountCard()}
    ${renderDeskLead({
      eyebrow: desk.eyebrow,
      regime: scanner.regime,
      badge: scanner.data_mode,
      headline: localizeText(scanner.headline),
      role: desk.role,
      question: desk.question,
      nextAction: localizeText(scanner.next_action),
      provider: marketProvider,
      updatedAt: marketUpdatedAt,
      cached: scanner.data_cached,
      stale: scanner.data_stale,
    })}

    ${renderStatCards(scannerStatCards)}

    ${renderTradingViewPanel({
      symbol: chartSymbol,
      title: desk.chartTitle,
      watchlist: chartWatchlist,
    })}

    <section class="market-assets">
      ${scanner.candidates
        .map((candidate) => renderScannerCard(candidate, level, text))
        .join("")}
    </section>

    ${renderDeskNotes(
      desk.noteTitle,
      level === "beginner"
        ? [
            "Keep only a few ideas in view.",
            "Watch the trigger, not every candle.",
            "Let alerts bring the market back to you.",
          ]
        : level === "medium"
          ? [
              "Start with the hottest names before building names.",
              "Use trigger plans to guide attention and timing.",
              "Keep alerts armed so Scanner stays focused.",
            ]
          : [
              "Start with Hot names before spending attention on Building ones.",
              "Use the trigger plan to decide if the setup is alive, not just interesting.",
              "Keep alerts armed so Scanner can reduce chart babysitting.",
            ],
      text.settingsActions.back,
    )}
  `);
}

function renderWelcome() {
  const text = getText();
  return shell(`
    ${renderAccountCard()}
    <section class="hero-card">
      <img class="hero-media" src="/assets/logo.svg" alt="ScannerHT logo" />
      <p class="eyebrow">${escapeHtml(text.labels.welcome)}</p>
      <h2 class="screen-title">${escapeHtml(text.welcomeTitle)}</h2>
      <p class="hero-copy">${escapeHtml(text.welcomeCopy)}</p>
      ${renderIdentityStrip()}
    </section>
    <section class="insight-grid">
      ${renderInsightBlock({
        eyebrow: text.desks.market.eyebrow,
        title: text.ui.marketInsightTitle,
        body: text.ui.marketInsightBody,
        items: [text.ui.regime, text.ui.sentiment, text.ui.volatility, text.ui.focusWindow],
      })}
      ${renderInsightBlock({
        eyebrow: text.desks.signals.eyebrow,
        title: text.ui.signalsInsightTitle,
        body: text.ui.signalsInsightBody,
        items: [text.ui.topSetup, text.ui.trigger, text.ui.conviction, text.ui.riskPosture],
      })}
      ${renderInsightBlock({
        eyebrow: text.desks.scanner.eyebrow,
        title: text.ui.scannerInsightTitle,
        body: text.ui.scannerInsightBody,
        items: [text.ui.discovery, text.scanner.urgency, text.ui.triggerPlan, text.ui.alertReadiness],
      })}
      ${renderInsightBlock({
        eyebrow: text.desks.alerts.eyebrow,
        title: text.ui.alertsInsightTitle,
        body: text.ui.alertsInsightBody,
        items: [text.ui.threshold, text.ui.deliveryStatus, text.ui.nextReturnWindow],
      })}
    </section>
    <section class="menu-grid">
      ${text.menu
        .map(
          ({ key, icon, title, description }) => `
            <button class="menu-button" data-action="${getMenuAction(key)}" data-value="${key}">
              <span>${icon}</span>
              <strong>${escapeHtml(title)}</strong>
              <span class="helper-text">${escapeHtml(description)}</span>
            </button>
          `,
        )
        .join("")}
    </section>
  `);
}

function renderSettings() {
  const text = getText();
  const user = state.user;
  return shell(`
    ${renderAccountCard()}
    <section class="screen-card">
      <div class="screen-head">
        <div>
          <p class="eyebrow">${escapeHtml(text.ui.profileEyebrow)}</p>
          <h2 class="screen-title">${escapeHtml(text.settingsTitle)}</h2>
        </div>
        <span class="setup-badge">${escapeHtml(text.labels.welcome)}</span>
      </div>
      <p class="screen-copy">${escapeHtml(text.settingsCopy)}</p>
      ${renderIdentityStrip()}
    </section>

    <section class="insight-grid">
      ${renderInsightBlock({
        eyebrow: text.labels.level,
        title: valueLabel("level", user.level),
        body: text.ui.levelBehavior,
        items: [
          `Scanner: ${formatScannerLimitValue(user)}`,
          `Alerts: ${getEffectiveAlertsPriority(user)}`,
          user.level === "beginner"
            ? text.ui.signalsSingle
            : user.level === "medium"
              ? text.ui.signalsGuided
              : text.ui.signalsDense,
        ],
      })}
      ${renderInsightBlock({
        eyebrow: text.labels.coins,
        title: text.ui.currentWatchlist,
        body: user.coins.length ? user.coins.join(", ") : text.labels.unset,
        items: [
          `${text.ui.languageField}: ${valueLabel("language", user.language)}`,
          `${text.ui.marketField}: ${valueLabel("market", user.market)}`,
          `${text.ui.styleField}: ${valueLabel("style", user.trading_style)}`,
        ],
      })}
    </section>

    <section class="screen-card">
      <div class="settings-summary">
        <div class="summary-row">
          <span class="summary-label">${escapeHtml(text.labels.language)}</span>
          <span class="summary-value">${escapeHtml(valueLabel("language", user.language))}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">${escapeHtml(text.labels.level)}</span>
          <span class="summary-value">${escapeHtml(valueLabel("level", user.level))}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">${escapeHtml(text.labels.scannerLimit)}</span>
          <span class="summary-value">${escapeHtml(formatScannerLimitValue(user))}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">${escapeHtml(text.labels.market)}</span>
          <span class="summary-value">${escapeHtml(valueLabel("market", user.market))}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">${escapeHtml(text.labels.style)}</span>
          <span class="summary-value">${escapeHtml(valueLabel("style", user.trading_style))}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">${escapeHtml(text.labels.coins)}</span>
          <span class="summary-value">${escapeHtml(user.coins.length ? user.coins.join(", ") : text.labels.unset)}</span>
        </div>
      </div>

      <div class="button-grid">
        <button class="secondary-button" data-action="settings-language">${escapeHtml(text.settingsActions.language)}</button>
        <button class="secondary-button" data-action="settings-level">${escapeHtml(text.settingsActions.level)}</button>
        ${user.level === "pro" ? `<button class="secondary-button" data-action="settings-scanner-limit">${escapeHtml(text.settingsActions.scannerLimit)}</button>` : ""}
        <button class="secondary-button" data-action="settings-market">${escapeHtml(text.settingsActions.market)}</button>
        <button class="secondary-button" data-action="settings-style">${escapeHtml(text.settingsActions.style)}</button>
        <button class="secondary-button" data-action="settings-coins">${escapeHtml(text.settingsActions.coins)}</button>
      </div>

      <div class="screen-actions">
        <button class="secondary-button" data-action="reset-user">${escapeHtml(text.settingsActions.reset)}</button>
        <button class="primary-button" data-action="back-main">${escapeHtml(text.settingsActions.back)}</button>
      </div>
    </section>
  `);
}

function renderHelp() {
  const text = getText();
  const user = state.user;
  return shell(`
    ${renderAccountCard()}
    <section class="hero-card">
      <p class="eyebrow">${escapeHtml(text.ui.helpEyebrow)}</p>
      <h2 class="screen-title">${escapeHtml(text.ui.helpTitle)}</h2>
      <p class="hero-copy">${escapeHtml(text.ui.helpCopy)}</p>
      ${renderIdentityStrip()}
    </section>
    <section class="insight-grid">
      ${renderInsightBlock({
        eyebrow: "1",
        title: text.menu[0].title,
        body: text.ui.marketInsightBody,
        items: [text.ui.regime, text.ui.sentiment, text.ui.volatility, text.ui.focusWindow],
      })}
      ${renderInsightBlock({
        eyebrow: "2",
        title: text.menu[1].title,
        body: text.ui.signalsInsightBody,
        items: [
          user.level === "beginner" ? text.ui.oneMainSetup : text.ui.executionReady,
          text.ui.trigger,
          text.ui.conviction,
          user.level === "beginner" ? text.ui.simpleAction : text.ui.riskInvalidation,
        ],
      })}
      ${renderInsightBlock({
        eyebrow: "3",
        title: text.menu[2].title,
        body: text.ui.scannerInsightBody,
        items: [text.ui.queue, text.scanner.urgency, text.ui.triggerPlan, text.ui.alertReadiness],
      })}
      ${renderInsightBlock({
        eyebrow: "4",
        title: text.menu[3].title,
        body: text.ui.alertsInsightBody,
        items: [
          `${text.ui.threshold}: ${getEffectiveAlertsPriority(user)}`,
          text.ui.deliveryStatus,
          text.ui.nextReturnWindow,
        ],
      })}
    </section>
    <section class="screen-card">
      <div class="screen-actions">
        <button class="secondary-button" data-action="open-settings">${escapeHtml(text.settingsActions.back)}</button>
        <button class="primary-button" data-action="back-main">${escapeHtml(text.ui.cockpit)}</button>
      </div>
    </section>
  `);
}

function buttonChoice(label, action, value) {
  return `<button class="secondary-button" data-action="${action}" data-value="${value}">${label}</button>`;
}

function secondaryAction(label, action) {
  return `<button class="secondary-button" data-action="${action}">${escapeHtml(label)}</button>`;
}

function renderCurrentView() {
  renderHeader();

  if (state.loading) {
    appRoot.innerHTML = renderLoading();
    attachSharedEvents();
    return;
  }

  if (!state.user) {
    appRoot.innerHTML = renderAuthCard();
    attachSharedEvents();
    mountTelegramWidget();
    return;
  }

  const text = getText();

  if (state.view === "settings") {
    appRoot.innerHTML = renderSettings();
  } else if (state.view === "market") {
    appRoot.innerHTML = renderMarket();
  } else if (state.view === "signals") {
    appRoot.innerHTML = renderSignals();
  } else if (state.view === "alerts") {
    appRoot.innerHTML = renderAlerts();
  } else if (state.view === "scanner") {
    appRoot.innerHTML = renderScanner();
  } else if (state.view === "help") {
    appRoot.innerHTML = renderHelp();
  } else if (state.view === "settings-language") {
    appRoot.innerHTML = renderChoiceScreen({
      badge: text.settingsTitle,
      title: text.settingsActions.language,
      description: text.settingsCopy,
      buttons: [
        buttonChoice("🇫🇷 Français", "language", "fr"),
        buttonChoice("🇺🇸 English", "language", "en"),
        buttonChoice("🇪🇸 Español", "language", "es"),
        secondaryAction(text.settingsActions.back, "open-settings"),
      ],
    });
  } else if (state.view === "settings-level") {
    appRoot.innerHTML = renderChoiceScreen({
      badge: text.settingsTitle,
      title: text.settingsActions.level,
      description: text.settingsCopy,
      buttons: [
        buttonChoice(`🌱 ${valueLabel("level", "beginner")}`, "level", "beginner"),
        buttonChoice(`🧭 ${valueLabel("level", "medium")}`, "level", "medium"),
        buttonChoice(`⚔️ ${valueLabel("level", "pro")}`, "level", "pro"),
        secondaryAction(text.settingsActions.back, "open-settings"),
      ],
    });
  } else if (state.view === "settings-scanner-limit") {
    appRoot.innerHTML = renderScannerLimitScreen();
  } else if (state.view === "settings-market") {
    appRoot.innerHTML = renderChoiceScreen({
      badge: text.settingsTitle,
      title: text.settingsActions.market,
      description: text.settingsCopy,
      buttons: [
        buttonChoice("📊 Spot", "market", "spot"),
        buttonChoice("⚡ Futures", "market", "futures"),
        secondaryAction(text.settingsActions.back, "open-settings"),
      ],
    });
  } else if (state.view === "settings-style") {
    appRoot.innerHTML = renderChoiceScreen({
      badge: text.settingsTitle,
      title: text.settingsActions.style,
      description: text.settingsCopy,
      buttons: [
        buttonChoice("⚡ Scalping", "style", "scalping"),
        buttonChoice("📈 Intraday", "style", "intraday"),
        secondaryAction(text.settingsActions.back, "open-settings"),
      ],
    });
  } else if (state.view === "settings-coins") {
    appRoot.innerHTML = renderCoinsScreen(true);
  } else if (state.user.next_step === "intro") {
    appRoot.innerHTML = shell(`
      ${renderAccountCard()}
      <section class="hero-card">
        <img class="hero-media" src="/assets/logo.svg" alt="ScannerHT logo" />
        <p class="eyebrow">${escapeHtml(text.ui.introEyebrow)}</p>
        <h2 class="hero-title">${escapeHtml(text.authTitle)}</h2>
        <p class="hero-copy">${escapeHtml(text.authCopy)}</p>
        <div class="hero-actions">
          <button class="primary-button" data-action="intro-begin">🚀 ${escapeHtml(text.labels.welcome)}</button>
        </div>
      </section>
    `);
  } else if (state.user.next_step === "language") {
    appRoot.innerHTML = renderChoiceScreen({
      badge: `${text.ui.setup} 0/5`,
      title: text.languageTitle,
      description: text.ui.languageSetupCopy,
      buttons: [
        buttonChoice("🇫🇷 Français", "language", "fr"),
        buttonChoice("🇺🇸 English", "language", "en"),
        buttonChoice("🇪🇸 Español", "language", "es"),
      ],
    });
  } else if (state.user.next_step === "level") {
    appRoot.innerHTML = renderChoiceScreen({
      badge: `${text.ui.setup} 1/5`,
      title: text.levelTitle,
      description: text.ui.levelSetupCopy,
      buttons: [
        buttonChoice(`🌱 ${valueLabel("level", "beginner")}`, "level", "beginner"),
        buttonChoice(`🧭 ${valueLabel("level", "medium")}`, "level", "medium"),
        buttonChoice(`⚔️ ${valueLabel("level", "pro")}`, "level", "pro"),
      ],
    });
  } else if (state.user.next_step === "market") {
    appRoot.innerHTML = renderChoiceScreen({
      badge: `${text.ui.setup} 2/5`,
      title: text.marketTitle,
      description: text.ui.marketSetupCopy,
      buttons: [
        buttonChoice("📊 Spot", "market", "spot"),
        buttonChoice("⚡ Futures", "market", "futures"),
      ],
    });
  } else if (state.user.next_step === "style") {
    appRoot.innerHTML = renderChoiceScreen({
      badge: `${text.ui.setup} 3/5`,
      title: text.styleTitle,
      description: text.ui.styleSetupCopy,
      buttons: [
        buttonChoice("⚡ Scalping", "style", "scalping"),
        buttonChoice("📈 Intraday", "style", "intraday"),
      ],
    });
  } else if (state.user.next_step === "coins") {
    appRoot.innerHTML = renderCoinsScreen(false);
  } else {
    appRoot.innerHTML = renderWelcome();
  }

  attachSharedEvents();
  mountTradingViewWidgets();
}

function mountTelegramWidget() {
  const slot = document.getElementById("telegram-login-slot");
  if (!slot) {
    return;
  }

  slot.innerHTML = "";

  if (!state.config?.telegram_login_enabled || !state.config?.telegram_bot_username) {
    return;
  }

  const script = document.createElement("script");
  script.src = "https://telegram.org/js/telegram-widget.js?22";
  script.async = true;
  script.setAttribute("data-telegram-login", state.config.telegram_bot_username);
  script.setAttribute("data-size", "large");
  script.setAttribute("data-radius", "18");
  script.setAttribute("data-userpic", "false");
  script.setAttribute("data-request-access", "write");
  script.setAttribute("data-onauth", "onTelegramAuth(user)");
  slot.appendChild(script);
}

function mountTradingViewWidgets() {
  const text = getText();
  appRoot.querySelectorAll("[data-tradingview-symbol]").forEach((container) => {
    const symbol = container.dataset.tradingviewSymbol || "BTC";
    const watchlistSymbols = JSON.parse(container.dataset.tradingviewWatchlist || "[]");
    const tradingViewSymbol = getTradingViewSymbol(symbol);
    const watchlist = watchlistSymbols.map((item) => getTradingViewSymbol(item));

    container.innerHTML = `
      <div class="tradingview-widget-container__widget"></div>
      <div class="tradingview-widget-copyright">
        <a href="${escapeHtml(buildTradingViewLink(symbol))}" rel="noopener nofollow" target="_blank">
          <span class="blue-text">${escapeHtml(symbol)} ${escapeHtml(text.ui.chartLinkSuffix)}</span>
        </a>
        <span class="trademark"> ${escapeHtml(text.ui.byTradingView)}</span>
      </div>
    `;

    const script = document.createElement("script");
    script.type = "text/javascript";
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: tradingViewSymbol,
      interval: getTradingViewInterval(),
      timezone: "Etc/UTC",
      theme: "dark",
      style: "1",
      locale: getTradingViewLocale(),
      withdateranges: true,
      allow_symbol_change: true,
      save_image: false,
      details: false,
      calendar: false,
      watchlist,
      support_host: "https://www.tradingview.com",
    });
    container.appendChild(script);
  });
}

function render() {
  renderCurrentView();
}

function attachSharedEvents() {
  appRoot.querySelectorAll("[data-action]").forEach((element) => {
    element.addEventListener("click", async () => {
      const { action, value } = element.dataset;

      if (action === "intro-begin") {
        await patchCurrentUser({ intro_seen: true });
        return;
      }

      if (action === "language") {
        const fromSettings = typeof state.view === "string" && state.view.startsWith("settings");
        state.view = fromSettings ? "settings" : null;
        const patch = { language: value };
        if (state.user.next_step === "language") {
          patch.level = null;
          patch.scanner_limit = null;
          patch.market = null;
          patch.trading_style = null;
          patch.coins = [];
        }
        await patchCurrentUser(patch);
        return;
      }

      if (action === "level") {
        const fromSettings = typeof state.view === "string" && state.view.startsWith("settings");
        state.view = fromSettings ? "settings" : null;
        await patchCurrentUser({ level: value });
        return;
      }

      if (action === "market") {
        const fromSettings = typeof state.view === "string" && state.view.startsWith("settings");
        state.view = fromSettings ? "settings" : null;
        await patchCurrentUser({ market: value });
        return;
      }

      if (action === "style") {
        const fromSettings = typeof state.view === "string" && state.view.startsWith("settings");
        state.view = fromSettings ? "settings" : null;
        await patchCurrentUser({ trading_style: value });
        return;
      }

      if (action === "coin" || action === "settings-coin") {
        const currentCoins = Array.isArray(state.user.coins) ? [...state.user.coins] : [];
        const isAddingFourthCoin = !currentCoins.includes(value) && currentCoins.length >= 3;

        if (isAddingFourthCoin) {
          state.error = getText().limitCoins;
          render();
          return;
        }

        const nextCoins = currentCoins.includes(value)
          ? currentCoins.filter((coin) => coin !== value)
          : [...currentCoins, value];

        if (action === "settings-coin") {
          state.view = nextCoins.length === 3 ? "settings" : "settings-coins";
        }

        await patchCurrentUser({ coins: nextCoins });
        return;
      }

      if (action === "open-settings") {
        state.view = "settings";
        render();
        return;
      }

      if (action === "open-help") {
        state.view = "help";
        render();
        return;
      }

      if (action === "open-market") {
        state.loading = true;
        state.error = "";
        render();
        try {
          await loadMarket();
          state.view = "market";
        } catch (error) {
          state.error = extractErrorMessage(error);
        } finally {
          state.loading = false;
          render();
        }
        return;
      }

      if (action === "open-signals") {
        state.loading = true;
        state.error = "";
        render();
        try {
          await loadSignals();
          state.view = "signals";
        } catch (error) {
          state.error = extractErrorMessage(error);
        } finally {
          state.loading = false;
          render();
        }
        return;
      }

      if (action === "open-alerts") {
        state.loading = true;
        state.error = "";
        render();
        try {
          await loadAlerts();
          state.view = "alerts";
        } catch (error) {
          state.error = extractErrorMessage(error);
        } finally {
          state.loading = false;
          render();
        }
        return;
      }

      if (action === "open-scanner") {
        state.loading = true;
        state.error = "";
        render();
        try {
          await loadScanner();
          state.view = "scanner";
        } catch (error) {
          state.error = extractErrorMessage(error);
        } finally {
          state.loading = false;
          render();
        }
        return;
      }

      if (action === "scanner-limit-save") {
        const input = document.getElementById("scanner-limit-select");
        const nextLimit = Number(input?.value || getEffectiveScannerLimit(state.user));
        state.view = "settings";
        await patchCurrentUser({ scanner_limit: nextLimit });
        return;
      }

      if (action === "alerts-enable" || action === "alerts-disable" || action === "alerts-priority") {
        if (action === "alerts-priority" && getUserLevel(state.user) !== "pro") {
          return;
        }
        const patch =
          action === "alerts-priority"
            ? { alerts_min_priority: value }
            : { alerts_enabled: action === "alerts-enable" };
        state.loading = true;
        state.error = "";
        render();
        try {
          state.user = await apiRequest("/web/me", {
            method: "PATCH",
            body: JSON.stringify(patch),
          });
          await loadAlerts();
          state.view = "alerts";
        } catch (error) {
          state.error = extractErrorMessage(error);
        } finally {
          state.loading = false;
          render();
        }
        return;
      }

      if (
        action === "settings-language" ||
        action === "settings-level" ||
        action === "settings-scanner-limit" ||
        action === "settings-market" ||
        action === "settings-style" ||
        action === "settings-coins"
      ) {
        state.view = action;
        render();
        return;
      }

      if (action === "reset-user") {
        await resetCurrentUser();
        return;
      }

      if (action === "back-main") {
        state.view = null;
        render();
        return;
      }

      if (action === "placeholder") {
        state.error = `${value} ${getText().ui.modulePending}`;
        render();
      }
    });
  });
}

sessionButton.addEventListener("click", async () => {
  if (!state.user) {
    render();
    return;
  }

  await logout();
});

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function init() {
  state.loading = true;
  render();

  try {
    await loadConfig();
    await loadCurrentUser();
  } catch (error) {
    state.error = extractErrorMessage(error);
  } finally {
    state.loading = false;
    render();
  }
}

init();
