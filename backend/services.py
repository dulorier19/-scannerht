import hashlib
import json
import math
import re
import sqlite3
import time
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib import parse, request

from .config import ALERT_MIN_INTERVAL_SECONDS, DB_PATH, MARKET_DATA_CACHE_SECONDS, MARKET_DATA_MODE, MARKET_DATA_PROVIDER
from .db import TRADE_EVENTS_TABLE_SQL, TRADE_JOURNAL_TABLE_SQL, row_to_trade_event_record, row_to_trade_journal_record

ALLOWED_LANGUAGES = {"fr", "en", "es"}
ALLOWED_LEVELS = {"beginner", "medium", "pro"}
ALLOWED_MARKETS = {"spot", "futures"}
ALLOWED_TRADING_STYLES = {"scalping", "intraday"}
ALERT_PRIORITIES = ("high", "medium", "low")
DEFAULT_MARKET_COINS = ["BTC", "ETH", "SOL"]
SCANNER_DISCOVERY_COINS = ["BTC", "ETH", "SOL", "DOGE", "AVAX", "MATIC", "LINK", "DOT"]
MIN_SCANNER_LIMIT = 3
MEDIUM_SCANNER_LIMIT = 5
MAX_SCANNER_LIMIT = len(SCANNER_DISCOVERY_COINS)
TRADEPLAN_MIN_STOP_DISTANCE = {
    "low": 0.0035,
    "medium": 0.0050,
    "high": 0.0065,
}
BINANCE_SYMBOL_MAP = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "DOGE": "DOGEUSDT",
    "AVAX": "AVAXUSDT",
    "MATIC": "POLUSDT",
    "LINK": "LINKUSDT",
    "DOT": "DOTUSDT",
}
COINGECKO_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "MATIC": "polygon-ecosystem-token",
    "LINK": "chainlink",
    "DOT": "polkadot",
}
COINBASE_PRODUCT_MAP = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "DOGE": "DOGE-USD",
    "AVAX": "AVAX-USD",
    "MATIC": "POL-USD",
    "LINK": "LINK-USD",
    "DOT": "DOT-USD",
}
_LIVE_MARKET_CACHE: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
_TRADE_MANAGEMENT_JOB_QUEUE: dict[int, dict[str, dict[str, Any]]] = {}
_LOCALIZATION_RAW_FIELDS = {
    "user_id",
    "language",
    "level",
    "scanner_limit",
    "market_type",
    "trading_style",
    "data_mode",
    "data_provider",
    "data_updated_at",
    "data_cached",
    "data_stale",
    "delivery_status",
    "delivery_reason",
    "delivery_last_sent_at",
    "delivery_next_eligible_at",
    "delivery_cooldown_seconds",
    "digest_key",
    "alerts_enabled",
    "last_alert_digest",
    "last_alert_sent_at",
    "onboarding_complete",
    "active_message_id",
    "next_step",
    "symbol",
    "top_symbol",
    "last_price",
    "price_change_percent",
    "quote_volume",
    "trigger_price",
    "distance_percent",
    "pulse_score",
    "breakout_score",
    "volatility_score",
    "confidence",
    "ready_count",
    "watch_count",
    "cool_off_count",
    "high_priority_count",
    "medium_priority_count",
    "low_priority_count",
    "visible_count",
    "universe_size",
    "hot_count",
    "building_count",
    "early_count",
    "rank",
    "scanner_score",
    "watchlist_match",
    "alert_ready",
}
_LOCALIZATION_TERMS = {
    "fr": {
        "terms": {
            "Active": "Actif",
            "Watch": "Surveillance",
            "Stand aside": "Attente",
            "Hot": "Chaud",
            "Building": "Construction",
            "Early": "Tot",
            "Immediate": "Immediate",
            "Near": "Proche",
            "Monitor": "Surveiller",
            "High": "Haute",
            "Medium": "Moyenne",
            "Low": "Basse",
            "High conviction": "Conviction forte",
            "Building conviction": "Conviction en construction",
            "Low conviction": "Conviction faible",
            "Long bias": "Biais haussier",
            "Watch for reclaim": "Surveiller la reprise",
            "Wait": "Attendre",
            "Ready": "Pret",
            "Cool-off": "Pause",
            "Trend continuation": "Tendance de continuation",
            "Breakout watch": "Surveillance de cassure",
            "Range / reset": "Range / reinitialisation",
            "Fast momentum": "Momentum rapide",
            "Session range": "Range de session",
            "Risk-on continuation": "Continuation haussiere",
            "Selective continuation": "Continuation selective",
            "Defensive chop": "Chop defensif",
            "Explosive": "Explosive",
            "Compressed": "Compressee",
            "Fast reaction window": "Fenetre de reaction rapide",
            "Session continuation window": "Fenetre de continuation de session",
            "5m-15m execution": "Execution 5m-15m",
            "1h-4h execution": "Execution 1h-4h",
            "15m-1h follow-up": "Suivi 15m-1h",
            "1h-4h follow-up": "Suivi 1h-4h",
            "5m-30m scan loop": "Boucle de scan 5m-30m",
            "30m-4h scan loop": "Boucle de scan 30m-4h",
            "Continuation confirm": "Confirmation de continuation",
            "Bullish confirmation": "Confirmation haussiere",
            "Reclaim trigger": "Declenchement de reprise",
            "Reclaim watch": "Surveillance de reprise",
            "Recovery trigger": "Declenchement de reprise",
            "Standby recovery": "Reprise en attente",
            "Long continuation": "Continuation haussiere",
            "Momentum reclaim": "Reprise de momentum",
            "No edge yet": "Pas d'avantage clair",
        },
        "replacements": [
            ("Reduced size until momentum confirms clean continuation.", "Taille reduite jusqu'a confirmation claire du momentum."),
            ("Trade only confirmed breaks and avoid late entries.", "Trade seulement les cassures confirmees et evite les entrees tardives."),
            ("Normal risk is acceptable, but only with structure in your favor.", "Le risque normal reste acceptable, mais seulement avec une structure en ta faveur."),
            ("No size. Keep it on alerts only until structure improves.", "Aucune taille. Garde cette idee en alertes seulement jusqu'a amelioration de la structure."),
            ("Start with reduced size and add only after a clean confirmation.", "Commence avec une taille reduite et ajoute seulement apres une confirmation propre."),
            ("Start normal size only after confirmation. Add only if follow-through holds.", "Commence la taille normale seulement apres confirmation. Ajoute seulement si la continuation tient."),
            ("Use starter size only if the trigger confirms. Avoid full size on anticipation.", "Utilise seulement une petite taille si le trigger confirme. Evite la taille complete sur anticipation."),
            ("Enter only after the next confirmation candle holds.", "Entre seulement si la prochaine bougie de confirmation tient."),
            ("Wait for a reclaim trigger before opening risk.", "Attends un trigger de reprise avant d'ouvrir du risque."),
            ("No trigger yet. Leave it on standby.", "Pas encore de trigger. Laisse cette idee en attente."),
            ("Act only if price holds above ", "Agis seulement si le prix tient au-dessus de "),
            ("Trigger only on a reclaim through ", "Declenche seulement sur reprise au-dessus de "),
            ("Stand aside until price reclaims ", "Reste a l'ecart jusqu'a reprise au-dessus de "),
            ("Abort if price loses ", "Abandonne si le prix repasse sous "),
            ("Stay flat if price keeps closing below ", "Reste a plat si le prix continue de cloturer sous "),
            ("Skip it until structure repairs above ", "Ignore cette idee tant que la structure ne se repare pas au-dessus de "),
            ("Stand down if price slips back under ", "Abandonne si le prix repasse sous "),
            (" after confirmation.", " apres confirmation."),
            (" with follow-through.", " avec continuite."),
            (" and the reclaim never sticks.", " et que la reprise ne tient pas."),
            (" with momentum.", " avec impulsion."),
            (" after the confirmation instead of holding above it.", " apres la confirmation au lieu de tenir au-dessus."),
            (" after the trigger instead of holding above it.", " apres le trigger au lieu de tenir au-dessus."),
            (" and momentum fades.", " et que le momentum s'affaiblit."),
            ("Downgraded because the broader tape is defensive. Wait for stronger confirmation.", "Degrade parce que le marche global reste defensif. Attends une confirmation plus forte."),
            ("Downgraded because the broader tape is defensive and the reclaim is still weak.", "Degrade parce que le marche global reste defensif et que la reprise reste faible."),
            ("Downgraded because volatility is still too fast for a clean first entry.", "Degrade parce que la volatilite reste trop rapide pour une premiere entree propre."),
            ("Downgraded because volatility is too unstable for a reclaim setup right now.", "Degrade parce que la volatilite reste trop instable pour un setup de reprise maintenant."),
            ("High velocity. Cut size and avoid chasing extension candles.", "Vitesse elevee. Reduis la taille et evite de chasser les bougies d'extension."),
            ("Moderate volatility. Wait for confirmation before committing full size.", "Volatilite moderee. Attends la confirmation avant de prendre la taille complete."),
            ("Controlled conditions. Favor clean structure over speed.", "Conditions controlees. Favorise une structure propre plutot que la vitesse."),
            (" setup. Enter only if strength holds after the next confirmation.", " : entre seulement si la force tient apres la prochaine confirmation."),
            (" setup. Wait for confirmation before opening risk.", " : attends la confirmation avant d'ouvrir du risque."),
            ("No clean trigger yet. Protect capital and wait for structure to improve.", "Pas encore de trigger propre. Protege le capital et attends que la structure s'ameliore."),
            ("Several setups are aligned. Focus on the cleanest continuation instead of forcing all of them.", "Plusieurs setups sont alignes. Concentre-toi sur la continuation la plus propre au lieu de tout forcer."),
            ("One setup stands out. Let the rest confirm before spreading attention too wide.", "Un setup se detache. Laisse le reste confirmer avant de trop disperser ton attention."),
            ("Watchlist is forming, but confirmation still matters more than anticipation.", "La watchlist se construit, mais la confirmation compte encore plus que l'anticipation."),
            ("No strong signal right now. Capital preservation is the active decision.", "Pas de signal fort pour l'instant. La preservation du capital reste la vraie decision."),
            ("Prioritize ", "Priorise "),
            (" first and keep the others as secondary ideas.", " en premier et garde les autres comme idees secondaires."),
            ("Focus on ", "Concentre-toi sur "),
            (" and act only if its trigger confirms cleanly.", " et n'agis que si son trigger confirme proprement."),
            ("Keep ", "Garde "),
            (" at the top of the watchlist and wait for the reclaim trigger.", " en tete de watchlist et attends le trigger de reprise."),
            ("Stay selective. Keep alerts on and wait for structure plus momentum to improve.", "Reste selectif. Garde les alertes actives et attends que la structure et le momentum s'ameliorent."),
            ("Act only on setups marked Active after confirmation, never before it.", "Agis seulement sur les setups marques Actif apres confirmation, jamais avant."),
            ("Use the trigger line to decide entry and the size plan to control exposure.", "Utilise la ligne de trigger pour decider l'entree et le plan de taille pour controler l'exposition."),
            ("Skip Stand aside names until both structure and momentum improve together.", "Ignore les idees en Attente jusqu'a ce que structure et momentum s'ameliorent ensemble."),
            ("Price is close to a valid continuation trigger. Stay ready for confirmation.", "Le prix est proche d'un trigger de continuation valide. Reste pret pour la confirmation."),
            ("Structure is active, but trigger quality still needs a cleaner confirmation.", "La structure est active, mais la qualite du trigger demande encore une confirmation plus propre."),
            ("Structure is improving, but it still needs a reclaim before risk makes sense.", "La structure s'ameliore, mais elle a encore besoin d'une reprise avant que le risque fasse sens."),
            ("No clean edge yet. Only a stronger recovery should bring this back into focus.", "Pas d'avantage propre pour l'instant. Seule une reprise plus forte devrait remettre cette idee en focus."),
            ("Alert on breakout confirmation, then execute only if follow-through holds.", "Alerte sur confirmation de cassure, puis execute seulement si le mouvement tient."),
            ("Let the alert bring the pair back to you instead of front-running the move.", "Laisse l'alerte ramener la paire a toi au lieu d'anticiper le mouvement."),
            ("Keep it on alerts only and skip active risk until the structure resets.", "Garde cette idee en alertes seulement et evite le risque actif tant que la structure ne se remet pas en place."),
            ("Several alert candidates are close. Let alerts bring the market to you instead of camping on the chart.", "Plusieurs alertes se rapprochent. Laisse les alertes ramener le marche a toi au lieu de rester colle au chart."),
            ("One alert stands out as the clearest near-term trigger.", "Une alerte ressort comme le trigger le plus clair a court terme."),
            ("The watchlist is constructive, but most moves still need confirmation.", "La watchlist est constructive, mais la plupart des mouvements demandent encore une confirmation."),
            ("Nothing needs urgent attention right now. Alerts should protect focus, not create noise.", "Rien ne demande une attention urgente pour l'instant. Les alertes doivent proteger le focus, pas creer du bruit."),
            ("Arm the high-priority flow around ", "Arme d'abord le flux de haute priorite autour de "),
            (" first, then review the secondary names.", " puis revois ensuite les noms secondaires."),
            (" on top of your alerts and only react if the trigger prints cleanly.", " en tete de tes alertes et reagis seulement si le trigger imprime proprement."),
            ("Set reclaim alerts for ", "Place des alertes de reprise pour "),
            (" and let the market come to your level.", " et laisse le marche venir a ton niveau."),
            ("Stay selective. Keep only low-noise alerts active and wait for the structure to improve.", "Reste selectif. Garde seulement des alertes peu bruyantes et attends que la structure s'ameliore."),
            ("Telegram alert delivery is cooling down for ", "La livraison Telegram est en cooldown pour les idees "),
            ("High+", "Haute+"),
            ("Medium+", "Moyenne+"),
            ("Low+", "Basse+"),
            (" ideas. Next window in about ", " et plus. Prochaine fenetre dans environ "),
            (" min.", " min."),
            ("Telegram alert delivery is armed for ", "La livraison Telegram est armee pour les idees "),
            (" ideas.", "."),
            (" Cooldown: about ", " Cooldown : environ "),
            (" min between repeated digests.", " min entre deux digests repetes."),
            ("Telegram delivery is off. Arm alerts to receive ", "La livraison Telegram est coupee. Arme les alertes pour recevoir les idees "),
            (" ideas without camping on charts.", " et plus sans rester colle aux graphiques."),
            ("Scanner sees multiple names close to execution. Focus the first pass on the hottest trigger, not the whole list.", "Le Scanner voit plusieurs noms proches de l'execution. Concentre le premier passage sur le trigger le plus chaud, pas sur toute la liste."),
            ("One scanner candidate stands above the rest right now.", "Un candidat Scanner se detache du reste pour l'instant."),
            ("Scanner is finding constructive structures, but most still need proof before they deserve full attention.", "Le Scanner trouve des structures constructives, mais la plupart ont encore besoin de preuve avant de meriter toute ton attention."),
            ("Scanner is quiet enough to protect your focus. No need to force activity while structure is still early.", "Le Scanner est assez calme pour proteger ton focus. Inutile de forcer l'activite tant que la structure reste precoce."),
            ("Work top-down: start with ", "Travaille du haut vers le bas : commence par "),
            (", then keep the second hot name as backup.", ", puis garde le second nom chaud en secours."),
            (" in front of you and let the trigger decide the trade, not anticipation.", " devant toi et laisse le trigger decider du trade, pas l'anticipation."),
            ("Queue ", "Mets "),
            (" first and use alerts to avoid watching every candle.", " en tete et utilise les alertes pour eviter de surveiller chaque bougie."),
            ("Stay selective, keep alerts armed, and wait for a cleaner quality cluster to form.", "Reste selectif, garde les alertes armees et attends qu'un groupe d'idees plus propre se forme."),
            (" around ", " vers "),
            (" | ", " | "),
            ("Live tape shows momentum leadership across your selected watchlist.", "Le flux live montre un leadership de momentum sur ta watchlist selectionnee."),
            ("Live tape is mixed, so selection and timing matter more than broad direction.", "Le flux live est mitige, donc la selection et le timing comptent plus que la direction generale."),
            ("Live tape is defensive right now, so patience matters more than forcing entries.", "Le flux live est defensif pour l'instant, donc la patience compte plus que les entrees forcees."),
            ("Momentum is broadening across your watchlist.", "Le momentum s'elargit sur ta watchlist."),
            ("Leadership is narrow, so coin selection matters more than direction.", "Le leadership est etroit, donc la selection des coins compte plus que la direction."),
            ("Prioritize coins with pulse score above 70 before taking aggressive entries.", "Priorise les coins avec un pulse score au-dessus de 70 avant les entrees agressives."),
            ("Reduce size when volatility is explosive and the breakout score is below 60.", "Reduis la taille quand la volatilite est explosive et que le breakout score reste sous 60."),
            ("Wait for alignment between pulse and breakout before chasing late moves.", "Attends l'alignement entre pulse et breakout avant de chasser des mouvements tardifs."),
            ("Prioritize assets with positive 24h change and breakout score above 65.", "Priorise les actifs avec variation 24h positive et breakout score au-dessus de 65."),
            ("Reduce size when volatility expands but price closes far from the 24h high.", "Reduis la taille quand la volatilite s'elargit mais que le prix cloture loin du plus haut 24h."),
            ("Use the live badge as confirmation, not as a replacement for trade risk management.", "Utilise le badge live comme confirmation, pas comme remplacement de la gestion du risque."),
            ("Confidence is strong because structure, trigger, and noise are aligned.", "La confiance est forte parce que la structure, le trigger et le bruit sont alignes."),
            ("Confidence is constructive, but confirmation still matters.", "La confiance est constructive, mais la confirmation compte encore."),
            ("Confidence is capped by noise. Wait for cleaner structure.", "La confiance est limitee par le bruit. Attends une structure plus propre."),
            ("Confidence is still building. Keep risk small until confirmation improves.", "La confiance est encore en construction. Garde un risque reduit jusqu'a meilleure confirmation."),
            ("Use one clear action, not constant monitoring.", "Utilise une action claire, pas une surveillance constante."),
            ("Wait for cleaner confirmation before reacting aggressively.", "Attends une confirmation plus propre avant de reagir agressivement."),
            ("Invalidation depends on structure. Re-check the chart before taking risk.", "L'invalidation depend de la structure. Recontrole le graphique avant de prendre du risque."),
            ("Invalidation depends on structure. Re-check before reacting.", "L'invalidation depend de la structure. Recontrole avant de reagir."),
            ("Invalidation depends on structure. Review the chart before acting.", "L'invalidation depend de la structure. Relis le graphique avant d'agir."),
            ("Futures scalping in explosive conditions. Demand cleaner confirmation and smaller size.", "Scalping futures en conditions explosives. Exige une confirmation plus propre et une taille plus petite."),
            ("Futures scalping context. Speed matters, but only with a clean trigger.", "Contexte futures scalping. La vitesse compte, mais seulement avec un trigger propre."),
            ("Futures context. Keep leverage selective and avoid weak continuation.", "Contexte futures. Garde le levier selectif et evite les continuations faibles."),
            ("Spot scalping context. Timing matters more than broad patience here.", "Contexte spot scalping. Le timing compte plus ici que la patience generale."),
            ("Spot intraday in defensive tape. Patience matters more than forcing entries.", "Spot intraday en marche defensif. La patience compte plus que les entrees forcees."),
            ("Spot intraday context. Let structure confirm before committing size.", "Contexte spot intraday. Laisse la structure confirmer avant d'engager la taille."),
            (" is leading with a cleaner trigger than the rest.", " mene avec un trigger plus propre que le reste."),
            (" is constructive, but still needs confirmation.", " est constructive, mais demande encore une confirmation."),
            (" is visible, but the edge is not clean enough yet.", " est visible, mais l'avantage n'est pas encore assez propre."),
        ],
    },
    "es": {
        "terms": {
            "Active": "Activo",
            "Watch": "Vigilancia",
            "Stand aside": "Espera",
            "Hot": "Caliente",
            "Building": "Construyendo",
            "Early": "Temprano",
            "Immediate": "Inmediato",
            "Near": "Cerca",
            "Monitor": "Vigilar",
            "High": "Alta",
            "Medium": "Media",
            "Low": "Baja",
            "High conviction": "Conviccion alta",
            "Building conviction": "Conviccion en construccion",
            "Low conviction": "Conviccion baja",
            "Long bias": "Sesgo alcista",
            "Watch for reclaim": "Vigilar recuperacion",
            "Wait": "Esperar",
            "Ready": "Listo",
            "Cool-off": "Pausa",
            "Trend continuation": "Continuacion de tendencia",
            "Breakout watch": "Vigilancia de ruptura",
            "Range / reset": "Rango / reinicio",
            "Fast momentum": "Momentum rapido",
            "Session range": "Rango de sesion",
            "Risk-on continuation": "Continuacion alcista",
            "Selective continuation": "Continuacion selectiva",
            "Defensive chop": "Chop defensivo",
            "Explosive": "Explosiva",
            "Compressed": "Comprimida",
            "Fast reaction window": "Ventana de reaccion rapida",
            "Session continuation window": "Ventana de continuacion de sesion",
            "5m-15m execution": "Ejecucion 5m-15m",
            "1h-4h execution": "Ejecucion 1h-4h",
            "15m-1h follow-up": "Seguimiento 15m-1h",
            "1h-4h follow-up": "Seguimiento 1h-4h",
            "5m-30m scan loop": "Bucle de escaneo 5m-30m",
            "30m-4h scan loop": "Bucle de escaneo 30m-4h",
            "Continuation confirm": "Confirmacion de continuacion",
            "Bullish confirmation": "Confirmacion alcista",
            "Reclaim trigger": "Trigger de recuperacion",
            "Reclaim watch": "Vigilancia de recuperacion",
            "Recovery trigger": "Trigger de recuperacion",
            "Standby recovery": "Recuperacion en espera",
            "Long continuation": "Continuacion alcista",
            "Momentum reclaim": "Recuperacion de momentum",
            "No edge yet": "Sin ventaja clara",
        },
        "replacements": [
            ("Reduced size until momentum confirms clean continuation.", "Tamano reducido hasta que el momentum confirme una continuacion limpia."),
            ("Trade only confirmed breaks and avoid late entries.", "Opera solo rupturas confirmadas y evita entradas tardias."),
            ("Normal risk is acceptable, but only with structure in your favor.", "El riesgo normal es aceptable, pero solo con la estructura a tu favor."),
            ("No size. Keep it on alerts only until structure improves.", "Sin tamano. Dejalo solo en alertas hasta que la estructura mejore."),
            ("Start with reduced size and add only after a clean confirmation.", "Empieza con tamano reducido y agrega solo despues de una confirmacion limpia."),
            ("Start normal size only after confirmation. Add only if follow-through holds.", "Empieza con tamano normal solo despues de la confirmacion. Agrega solo si la continuidad se sostiene."),
            ("Use starter size only if the trigger confirms. Avoid full size on anticipation.", "Usa tamano inicial solo si el trigger confirma. Evita tamano completo por anticipacion."),
            ("Enter only after the next confirmation candle holds.", "Entra solo si la siguiente vela de confirmacion se sostiene."),
            ("Wait for a reclaim trigger before opening risk.", "Espera un trigger de recuperacion antes de abrir riesgo."),
            ("No trigger yet. Leave it on standby.", "Todavia no hay trigger. Dejalo en espera."),
            ("Act only if price holds above ", "Actua solo si el precio se mantiene por encima de "),
            ("Trigger only on a reclaim through ", "Activa solo en recuperacion por encima de "),
            ("Stand aside until price reclaims ", "Mantente al margen hasta que el precio recupere "),
            ("Abort if price loses ", "Cancela si el precio pierde "),
            ("Stay flat if price keeps closing below ", "Mantente fuera si el precio sigue cerrando por debajo de "),
            ("Skip it until structure repairs above ", "Ignoralo hasta que la estructura se repare por encima de "),
            ("Stand down if price slips back under ", "Abandona si el precio vuelve por debajo de "),
            (" after confirmation.", " despues de la confirmacion."),
            (" with follow-through.", " con continuidad."),
            (" and the reclaim never sticks.", " y la recuperacion nunca se sostiene."),
            (" with momentum.", " con impulso."),
            (" after the confirmation instead of holding above it.", " despues de la confirmacion en lugar de sostenerse arriba."),
            (" after the trigger instead of holding above it.", " despues del trigger en lugar de sostenerse arriba."),
            (" and momentum fades.", " y el impulso se apaga."),
            ("Downgraded because the broader tape is defensive. Wait for stronger confirmation.", "Degradado porque el mercado amplio sigue defensivo. Espera una confirmacion mas fuerte."),
            ("Downgraded because the broader tape is defensive and the reclaim is still weak.", "Degradado porque el mercado amplio sigue defensivo y la recuperacion sigue debil."),
            ("Downgraded because volatility is still too fast for a clean first entry.", "Degradado porque la volatilidad sigue demasiado rapida para una primera entrada limpia."),
            ("Downgraded because volatility is too unstable for a reclaim setup right now.", "Degradado porque la volatilidad sigue demasiado inestable para un setup de recuperacion ahora."),
            ("High velocity. Cut size and avoid chasing extension candles.", "Velocidad alta. Reduce tamano y evita perseguir velas de extension."),
            ("Moderate volatility. Wait for confirmation before committing full size.", "Volatilidad moderada. Espera confirmacion antes de comprometer tamano completo."),
            ("Controlled conditions. Favor clean structure over speed.", "Condiciones controladas. Prioriza estructura limpia por encima de velocidad."),
            (" setup. Enter only if strength holds after the next confirmation.", " : entra solo si la fuerza se sostiene tras la siguiente confirmacion."),
            (" setup. Wait for confirmation before opening risk.", " : espera confirmacion antes de abrir riesgo."),
            ("No clean trigger yet. Protect capital and wait for structure to improve.", "Todavia no hay trigger limpio. Protege el capital y espera a que la estructura mejore."),
            ("Several setups are aligned. Focus on the cleanest continuation instead of forcing all of them.", "Varios setups estan alineados. Enfocate en la continuacion mas limpia en lugar de forzarlo todo."),
            ("One setup stands out. Let the rest confirm before spreading attention too wide.", "Un setup destaca. Deja que el resto confirme antes de dispersar demasiado tu atencion."),
            ("Watchlist is forming, but confirmation still matters more than anticipation.", "La watchlist se esta formando, pero la confirmacion sigue importando mas que la anticipacion."),
            ("No strong signal right now. Capital preservation is the active decision.", "No hay una senal fuerte ahora. Preservar capital sigue siendo la decision activa."),
            ("Prioritize ", "Prioriza "),
            (" first and keep the others as secondary ideas.", " primero y deja el resto como ideas secundarias."),
            ("Focus on ", "Enfocate en "),
            (" and act only if its trigger confirms cleanly.", " y actua solo si su trigger confirma limpiamente."),
            ("Keep ", "Manten "),
            (" at the top of the watchlist and wait for the reclaim trigger.", " en la parte alta de la watchlist y espera el trigger de recuperacion."),
            ("Stay selective. Keep alerts on and wait for structure plus momentum to improve.", "Sigue selectivo. Mantén alertas activas y espera a que estructura y momentum mejoren."),
            ("Act only on setups marked Active after confirmation, never before it.", "Actua solo en setups marcados como Activo despues de la confirmacion, nunca antes."),
            ("Use the trigger line to decide entry and the size plan to control exposure.", "Usa la linea del trigger para decidir la entrada y el plan de tamano para controlar la exposicion."),
            ("Skip Stand aside names until both structure and momentum improve together.", "Evita las ideas en Espera hasta que estructura y momentum mejoren juntas."),
            ("Price is close to a valid continuation trigger. Stay ready for confirmation.", "El precio esta cerca de un trigger de continuacion valido. Mantente listo para la confirmacion."),
            ("Structure is active, but trigger quality still needs a cleaner confirmation.", "La estructura esta activa, pero la calidad del disparador todavia necesita una confirmacion mas limpia."),
            ("Structure is improving, but it still needs a reclaim before risk makes sense.", "La estructura mejora, pero todavia necesita una recuperacion antes de que el riesgo tenga sentido."),
            ("No clean edge yet. Only a stronger recovery should bring this back into focus.", "Todavia no hay una ventaja limpia. Solo una recuperacion mas fuerte deberia devolver esto al foco."),
            ("Alert on breakout confirmation, then execute only if follow-through holds.", "Alerta en confirmacion de ruptura y ejecuta solo si la continuidad se sostiene."),
            ("Let the alert bring the pair back to you instead of front-running the move.", "Deja que la alerta te devuelva el par en lugar de anticipar el movimiento."),
            ("Keep it on alerts only and skip active risk until the structure resets.", "Dejalo solo en alertas y evita riesgo activo hasta que la estructura se reinicie."),
            ("Several alert candidates are close. Let alerts bring the market to you instead of camping on the chart.", "Varias alertas estan cerca. Deja que las alertas te traigan el mercado en lugar de quedarte pegado al grafico."),
            ("One alert stands out as the clearest near-term trigger.", "Una alerta destaca como el trigger mas claro de corto plazo."),
            ("The watchlist is constructive, but most moves still need confirmation.", "La watchlist es constructiva, pero la mayoria de movimientos aun necesita confirmacion."),
            ("Nothing needs urgent attention right now. Alerts should protect focus, not create noise.", "Nada necesita atencion urgente ahora. Las alertas deben proteger el foco, no crear ruido."),
            ("Arm the high-priority flow around ", "Activa primero el flujo de alta prioridad alrededor de "),
            (" first, then review the secondary names.", " y despues revisa los nombres secundarios."),
            (" on top of your alerts and only react if the trigger prints cleanly.", " en la parte alta de tus alertas y reacciona solo si el trigger aparece limpio."),
            ("Set reclaim alerts for ", "Configura alertas de recuperacion para "),
            (" and let the market come to your level.", " y deja que el mercado llegue a tu nivel."),
            ("Stay selective. Keep only low-noise alerts active and wait for the structure to improve.", "Sigue selectivo. Mantén solo alertas de bajo ruido y espera a que la estructura mejore."),
            ("Telegram alert delivery is cooling down for ", "La entrega de alertas por Telegram esta en cooldown para ideas "),
            ("High+", "Alta+"),
            ("Medium+", "Media+"),
            ("Low+", "Baja+"),
            (" ideas. Next window in about ", " y superiores. Proxima ventana en aproximadamente "),
            (" Cooldown: about ", " Cooldown: aproximadamente "),
            (" min between repeated digests.", " min entre digests repetidos."),
            ("Telegram alert delivery is armed for ", "La entrega de alertas por Telegram esta activa para ideas "),
            (" ideas.", "."),
            ("Telegram delivery is off. Arm alerts to receive ", "La entrega por Telegram esta apagada. Activa alertas para recibir ideas "),
            (" ideas without camping on charts.", " y superiores sin quedarte pegado a los graficos."),
            ("Scanner sees multiple names close to execution. Focus the first pass on the hottest trigger, not the whole list.", "Scanner ve varios nombres cerca de ejecucion. Enfoca la primera pasada en el trigger mas caliente, no en toda la lista."),
            ("One scanner candidate stands above the rest right now.", "Un candidato del Scanner destaca sobre el resto ahora mismo."),
            ("Scanner is finding constructive structures, but most still need proof before they deserve full attention.", "Scanner encuentra estructuras constructivas, pero la mayoria aun necesita prueba antes de merecer toda tu atencion."),
            ("Scanner is quiet enough to protect your focus. No need to force activity while structure is still early.", "Scanner esta lo bastante tranquilo para proteger tu foco. No hace falta forzar actividad mientras la estructura sigue temprana."),
            ("Work top-down: start with ", "Trabaja de arriba hacia abajo: empieza con "),
            (", then keep the second hot name as backup.", " y luego deja el segundo nombre caliente como respaldo."),
            (" in front of you and let the trigger decide the trade, not anticipation.", " frente a ti y deja que el trigger decida el trade, no la anticipacion."),
            ("Queue ", "Pon en cola "),
            (" first and use alerts to avoid watching every candle.", " primero y usa alertas para evitar mirar cada vela."),
            ("Stay selective, keep alerts armed, and wait for a cleaner quality cluster to form.", "Sigue selectivo, mantén alertas activas y espera a que se forme un grupo de ideas mas limpio."),
            (" around ", " cerca de "),
            ("watchlist", "lista de seguimiento"),
            ("trigger", "disparador"),
            ("Cooldown", "Enfriamiento"),
            ("digests", "resumenes"),
            ("Live tape shows momentum leadership across your selected watchlist.", "La cinta en vivo muestra liderazgo de momentum en tu watchlist seleccionada."),
            ("Live tape is mixed, so selection and timing matter more than broad direction.", "La cinta en vivo esta mixta, asi que la seleccion y el timing importan mas que la direccion general."),
            ("Live tape is defensive right now, so patience matters more than forcing entries.", "La cinta en vivo esta defensiva ahora, asi que la paciencia importa mas que forzar entradas."),
            ("Momentum is broadening across your watchlist.", "El momentum se esta ampliando en tu watchlist."),
            ("Leadership is narrow, so coin selection matters more than direction.", "El liderazgo es estrecho, asi que la seleccion de monedas importa mas que la direccion."),
            ("Prioritize coins with pulse score above 70 before taking aggressive entries.", "Prioriza monedas con pulse score por encima de 70 antes de tomar entradas agresivas."),
            ("Reduce size when volatility is explosive and the breakout score is below 60.", "Reduce tamano cuando la volatilidad sea explosiva y el breakout score este por debajo de 60."),
            ("Wait for alignment between pulse and breakout before chasing late moves.", "Espera alineacion entre pulse y breakout antes de perseguir movimientos tardios."),
            ("Prioritize assets with positive 24h change and breakout score above 65.", "Prioriza activos con cambio 24h positivo y breakout score por encima de 65."),
            ("Reduce size when volatility expands but price closes far from the 24h high.", "Reduce tamano cuando la volatilidad se expande pero el precio cierra lejos del maximo 24h."),
            ("Use the live badge as confirmation, not as a replacement for trade risk management.", "Usa la insignia live como confirmacion, no como reemplazo de la gestion de riesgo."),
            ("Confidence is strong because structure, trigger, and noise are aligned.", "La confianza es fuerte porque estructura, trigger y ruido estan alineados."),
            ("Confidence is constructive, but confirmation still matters.", "La confianza es constructiva, pero la confirmacion sigue importando."),
            ("Confidence is capped by noise. Wait for cleaner structure.", "La confianza queda limitada por el ruido. Espera una estructura mas limpia."),
            ("Confidence is still building. Keep risk small until confirmation improves.", "La confianza aun se esta construyendo. Mantén el riesgo pequeno hasta que mejore la confirmacion."),
            ("Use one clear action, not constant monitoring.", "Usa una accion clara, no una vigilancia constante."),
            ("Wait for cleaner confirmation before reacting aggressively.", "Espera una confirmacion mas limpia antes de reaccionar de forma agresiva."),
            ("Invalidation depends on structure. Re-check the chart before taking risk.", "La invalidacion depende de la estructura. Revisa el grafico antes de asumir riesgo."),
            ("Invalidation depends on structure. Re-check before reacting.", "La invalidacion depende de la estructura. Vuelve a revisar antes de reaccionar."),
            ("Invalidation depends on structure. Review the chart before acting.", "La invalidacion depende de la estructura. Revisa el grafico antes de actuar."),
            ("Futures scalping in explosive conditions. Demand cleaner confirmation and smaller size.", "Scalping en futures con condiciones explosivas. Exige confirmacion mas limpia y tamano menor."),
            ("Futures scalping context. Speed matters, but only with a clean trigger.", "Contexto futures scalping. La velocidad importa, pero solo con un trigger limpio."),
            ("Futures context. Keep leverage selective and avoid weak continuation.", "Contexto futures. Mantén el apalancamiento selectivo y evita continuaciones debiles."),
            ("Spot scalping context. Timing matters more than broad patience here.", "Contexto spot scalping. El timing importa mas aqui que la paciencia general."),
            ("Spot intraday in defensive tape. Patience matters more than forcing entries.", "Spot intradia en cinta defensiva. La paciencia importa mas que forzar entradas."),
            ("Spot intraday context. Let structure confirm before committing size.", "Contexto spot intradia. Deja que la estructura confirme antes de comprometer tamano."),
            (" is leading with a cleaner trigger than the rest.", " lidera con un trigger mas limpio que el resto."),
            (" is constructive, but still needs confirmation.", " es constructiva, pero todavia necesita confirmacion."),
            (" is visible, but the edge is not clean enough yet.", " es visible, pero la ventaja todavia no es lo bastante limpia."),
        ],
    },
}


def _stable_int(seed: str, minimum: int, maximum: int) -> int:
    digest = hashlib.sha256(seed.encode()).hexdigest()
    span = maximum - minimum + 1
    return minimum + (int(digest[:8], 16) % span)


def _localize_term(value: str, language: str | None) -> str:
    if not value or language not in _LOCALIZATION_TERMS:
        return value
    return _LOCALIZATION_TERMS[language]["terms"].get(value, value)


def _localize_text(value: str, language: str | None) -> str:
    if not value or language not in _LOCALIZATION_TERMS:
        return value

    localized = _localize_term(value, language)
    for source, target in sorted(
        _LOCALIZATION_TERMS[language]["replacements"],
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        localized = localized.replace(source, target)
    for source, target in sorted(
        _LOCALIZATION_TERMS[language]["terms"].items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        localized = re.sub(rf"\b{re.escape(source)}\b", target, localized, flags=re.IGNORECASE)
    return localized


def _localize_execution_bias(value: str, language: str | None) -> str:
    if not value or language not in {"fr", "es"}:
        return value

    replacements = {
        "fr": {
            "active": "actif",
            "watch": "surveillance",
            "stand aside": "attente",
        },
        "es": {
            "active": "activo",
            "watch": "vigilancia",
            "stand aside": "espera",
        },
    }[language]

    localized = value
    for source, target in replacements.items():
        localized = re.sub(rf"\b{re.escape(source)}\b", target, localized, flags=re.IGNORECASE)
    return localized


def _localize_payload(value: Any, language: str | None, field_name: str | None = None) -> Any:
    if language not in _LOCALIZATION_TERMS:
        return value

    if isinstance(value, dict):
        return {key: _localize_payload(item, language, key) for key, item in value.items()}
    if isinstance(value, list):
        return [_localize_payload(item, language, field_name) for item in value]
    if isinstance(value, str):
        if field_name in _LOCALIZATION_RAW_FIELDS:
            return value
        return _localize_text(value, language)
    return value


def _normalize_coin_list(coins: list[str] | tuple[str, ...] | None) -> list[str]:
    normalized: list[str] = []
    for symbol in coins or []:
        if not isinstance(symbol, str):
            continue
        normalized_symbol = symbol.upper()
        if normalized_symbol not in BINANCE_SYMBOL_MAP:
            continue
        if normalized_symbol not in normalized:
            normalized.append(normalized_symbol)
    return normalized


def update_trade_plan_stop_loss(
    direction: str,
    entry_price: float,
    initial_stop_loss: float,
    current_stop_loss: float,
    current_price: float,
    tp_hit_count: int,
    noise_level: str,
) -> float:
    direction_normalized = str(direction).strip().lower()
    if direction_normalized not in {"long", "short"}:
        raise ValueError("direction must be 'long' or 'short'.")

    noise_normalized = str(noise_level).strip().lower()
    if noise_normalized not in TRADEPLAN_MIN_STOP_DISTANCE:
        raise ValueError("noise_level must be 'low', 'medium', or 'high'.")

    for value_name, value in {
        "entry_price": entry_price,
        "initial_stop_loss": initial_stop_loss,
        "current_stop_loss": current_stop_loss,
        "current_price": current_price,
    }.items():
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"{value_name} must be a positive number.")

    tp_hits = max(0, int(tp_hit_count))
    min_distance = TRADEPLAN_MIN_STOP_DISTANCE[noise_normalized]

    if direction_normalized == "long":
        max_stop_for_distance = current_price * (1 - min_distance)
        protected_floor = max(initial_stop_loss, current_stop_loss)

        if tp_hits < 1:
            if protected_floor <= max_stop_for_distance:
                return float(protected_floor)
            return float(current_stop_loss)

        if tp_hits == 1:
            breakeven_guard = min(entry_price, max_stop_for_distance)
            tightened_stop = max(protected_floor, breakeven_guard)
            if tightened_stop <= max_stop_for_distance:
                return float(tightened_stop)
            return float(current_stop_loss)

        strengthened_stop = max(entry_price, max_stop_for_distance)
        tightened_stop = max(protected_floor, strengthened_stop)
        if tightened_stop <= max_stop_for_distance:
            return float(tightened_stop)
        return float(current_stop_loss)

    min_stop_for_distance = current_price * (1 + min_distance)
    protected_ceiling = min(initial_stop_loss, current_stop_loss)

    if tp_hits < 1:
        if protected_ceiling >= min_stop_for_distance:
            return float(protected_ceiling)
        return float(current_stop_loss)

    if tp_hits == 1:
        breakeven_guard = max(entry_price, min_stop_for_distance)
        tightened_stop = min(protected_ceiling, breakeven_guard)
        if tightened_stop >= min_stop_for_distance:
            return float(tightened_stop)
        return float(current_stop_loss)

    strengthened_stop = min(entry_price, min_stop_for_distance)
    tightened_stop = min(protected_ceiling, strengthened_stop)
    if tightened_stop >= min_stop_for_distance:
        return float(tightened_stop)
    return float(current_stop_loss)


def calculate_trade_plan_performance(
    direction: str,
    entry_price: float,
    initial_stop_loss: float,
    current_price: float,
    account_equity: float,
    risk_percent_per_trade: float,
    realized_r_multiple: float = 0.0,
    highest_price: float | None = None,
    lowest_price: float | None = None,
    market_type: str | None = None,
    trading_style: str | None = None,
) -> dict[str, float]:
    direction_normalized = str(direction).strip().lower()
    if direction_normalized not in {"long", "short"}:
        raise ValueError("direction must be 'long' or 'short'.")

    for value_name, value in {
        "entry_price": entry_price,
        "initial_stop_loss": initial_stop_loss,
        "current_price": current_price,
        "account_equity": account_equity,
        "risk_percent_per_trade": risk_percent_per_trade,
    }.items():
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"{value_name} must be a positive number.")

    if market_type == "futures" and trading_style == "scalping" and risk_percent_per_trade > 2:
        raise ValueError("futures/scalping trades require risk_percent_per_trade <= 2.")

    risk_unit = abs(entry_price - initial_stop_loss)
    if risk_unit <= 0:
        raise ValueError("entry_price and initial_stop_loss must define a non-zero initial risk.")
    risk_amount = (account_equity * risk_percent_per_trade) / 100

    favorable_reference = highest_price if isinstance(highest_price, (int, float)) and highest_price > 0 else current_price
    adverse_reference = lowest_price if isinstance(lowest_price, (int, float)) and lowest_price > 0 else current_price

    if direction_normalized == "long":
        unrealized_r_multiple = (current_price - entry_price) / risk_unit
        max_favorable_excursion = max(0.0, (favorable_reference - entry_price) / risk_unit)
        max_adverse_excursion = max(0.0, (entry_price - adverse_reference) / risk_unit)
    else:
        unrealized_r_multiple = (entry_price - current_price) / risk_unit
        max_favorable_excursion = max(0.0, (entry_price - adverse_reference) / risk_unit)
        max_adverse_excursion = max(0.0, (favorable_reference - entry_price) / risk_unit)

    realized_pnl_amount = float(realized_r_multiple) * risk_amount
    realized_pnl_percent = (realized_pnl_amount / account_equity) * 100
    unrealized_pnl_amount = float(unrealized_r_multiple) * risk_amount
    unrealized_pnl_percent = (unrealized_pnl_amount / account_equity) * 100

    return {
        "unrealized_r_multiple": float(unrealized_r_multiple),
        "realized_r_multiple": float(realized_r_multiple),
        "max_favorable_excursion": float(max_favorable_excursion),
        "max_adverse_excursion": float(max_adverse_excursion),
        "realized_pnl_amount": float(realized_pnl_amount),
        "realized_pnl_percent": float(realized_pnl_percent),
        "unrealized_pnl_amount": float(unrealized_pnl_amount),
        "unrealized_pnl_percent": float(unrealized_pnl_percent),
    }


def _trade_price_reached(direction: str, current_price: float, level: float | None) -> bool:
    if level is None:
        return False
    if direction == "long":
        return current_price >= level
    return current_price <= level


def _trade_stop_triggered(direction: str, current_price: float, stop_loss: float) -> bool:
    if direction == "long":
        return current_price <= stop_loss
    return current_price >= stop_loss


def _is_more_protective_stop(direction: str, previous_stop_loss: float, current_stop_loss: float) -> bool:
    if direction == "long":
        return current_stop_loss > previous_stop_loss
    return current_stop_loss < previous_stop_loss


def detect_trade_management_events(
    previous_plan: Any,
    current_plan: Any,
    current_price: float,
    *,
    invalidated: bool = False,
) -> list[dict[str, Any]]:
    if not isinstance(current_price, (int, float)) or current_price <= 0:
        raise ValueError("current_price must be a positive number.")

    if previous_plan.symbol != current_plan.symbol:
        raise ValueError("Trade management requires matching symbols.")
    if previous_plan.direction != current_plan.direction:
        raise ValueError("Trade management requires matching directions.")

    direction = current_plan.direction
    current_status = str(current_plan.status)
    events: list[dict[str, Any]] = []

    if previous_plan.tp_hit_count < 1 <= current_plan.tp_hit_count and _trade_price_reached(direction, current_price, current_plan.tp1):
        events.append(
            {
                "symbol": current_plan.symbol,
                "event_type": "tp1_hit",
                "direction": direction,
                "status": current_status,
                "current_price": float(current_price),
                "previous_stop_loss": float(previous_plan.current_stop_loss),
                "current_stop_loss": float(current_plan.current_stop_loss),
                "reference_price": float(current_plan.tp1) if current_plan.tp1 is not None else None,
                "detail": "First target reached.",
            }
        )

    if previous_plan.tp_hit_count < 2 <= current_plan.tp_hit_count and _trade_price_reached(direction, current_price, current_plan.tp2):
        events.append(
            {
                "symbol": current_plan.symbol,
                "event_type": "tp2_hit",
                "direction": direction,
                "status": current_status,
                "current_price": float(current_price),
                "previous_stop_loss": float(previous_plan.current_stop_loss),
                "current_stop_loss": float(current_plan.current_stop_loss),
                "reference_price": float(current_plan.tp2) if current_plan.tp2 is not None else None,
                "detail": "Second target reached.",
            }
        )

    if _trade_price_reached(direction, current_price, current_plan.tpf):
        events.append(
            {
                "symbol": current_plan.symbol,
                "event_type": "tpf_hit",
                "direction": direction,
                "status": current_status,
                "current_price": float(current_price),
                "previous_stop_loss": float(previous_plan.current_stop_loss),
                "current_stop_loss": float(current_plan.current_stop_loss),
                "reference_price": float(current_plan.tpf) if current_plan.tpf is not None else None,
                "detail": "Final target reached.",
            }
        )

    if _is_more_protective_stop(direction, previous_plan.current_stop_loss, current_plan.current_stop_loss):
        events.append(
            {
                "symbol": current_plan.symbol,
                "event_type": "sl_moved",
                "direction": direction,
                "status": current_status,
                "current_price": float(current_price),
                "previous_stop_loss": float(previous_plan.current_stop_loss),
                "current_stop_loss": float(current_plan.current_stop_loss),
                "reference_price": None,
                "detail": "Stop loss tightened.",
            }
        )

    if invalidated:
        events.append(
            {
                "symbol": current_plan.symbol,
                "event_type": "invalidated",
                "direction": direction,
                "status": current_status,
                "current_price": float(current_price),
                "previous_stop_loss": float(previous_plan.current_stop_loss),
                "current_stop_loss": float(current_plan.current_stop_loss),
                "reference_price": None,
                "detail": "Trade thesis invalidated.",
            }
        )
    elif _trade_stop_triggered(direction, current_price, current_plan.current_stop_loss):
        events.append(
            {
                "symbol": current_plan.symbol,
                "event_type": "stopped",
                "direction": direction,
                "status": current_status,
                "current_price": float(current_price),
                "previous_stop_loss": float(previous_plan.current_stop_loss),
                "current_stop_loss": float(current_plan.current_stop_loss),
                "reference_price": float(current_plan.current_stop_loss),
                "detail": "Stop loss hit.",
            }
        )

    return events


def format_trade_management_event_message(event: Any, language: str = "en") -> str:
    event_type = str(event["event_type"] if isinstance(event, dict) else event.event_type)
    symbol = str(event["symbol"] if isinstance(event, dict) else event.symbol)
    direction = str(event["direction"] if isinstance(event, dict) else event.direction).upper()
    current_price = float(event["current_price"] if isinstance(event, dict) else event.current_price)
    previous_stop_loss = event["previous_stop_loss"] if isinstance(event, dict) else event.previous_stop_loss
    current_stop_loss = event["current_stop_loss"] if isinstance(event, dict) else event.current_stop_loss
    reference_price = event["reference_price"] if isinstance(event, dict) else event.reference_price

    templates = {
        "en": {
            "tp1_hit": "{symbol} {direction}: TP1 hit near {reference_price:.2f}. Price {current_price:.2f}.",
            "tp2_hit": "{symbol} {direction}: TP2 hit near {reference_price:.2f}. Price {current_price:.2f}.",
            "tpf_hit": "{symbol} {direction}: final target hit near {reference_price:.2f}. Price {current_price:.2f}.",
            "sl_moved": "{symbol} {direction}: stop moved from {previous_stop_loss:.2f} to {current_stop_loss:.2f}.",
            "stopped": "{symbol} {direction}: stop hit at {current_stop_loss:.2f}.",
            "invalidated": "{symbol} {direction}: trade invalidated. Reassess the setup.",
        },
        "fr": {
            "tp1_hit": "{symbol} {direction}: TP1 touche vers {reference_price:.2f}. Prix {current_price:.2f}.",
            "tp2_hit": "{symbol} {direction}: TP2 touche vers {reference_price:.2f}. Prix {current_price:.2f}.",
            "tpf_hit": "{symbol} {direction}: cible finale touchee vers {reference_price:.2f}. Prix {current_price:.2f}.",
            "sl_moved": "{symbol} {direction}: stop deplace de {previous_stop_loss:.2f} a {current_stop_loss:.2f}.",
            "stopped": "{symbol} {direction}: stop touche a {current_stop_loss:.2f}.",
            "invalidated": "{symbol} {direction}: trade invalide. Reanalyse le setup.",
        },
        "es": {
            "tp1_hit": "{symbol} {direction}: TP1 alcanzado cerca de {reference_price:.2f}. Precio {current_price:.2f}.",
            "tp2_hit": "{symbol} {direction}: TP2 alcanzado cerca de {reference_price:.2f}. Precio {current_price:.2f}.",
            "tpf_hit": "{symbol} {direction}: objetivo final alcanzado cerca de {reference_price:.2f}. Precio {current_price:.2f}.",
            "sl_moved": "{symbol} {direction}: stop movido de {previous_stop_loss:.2f} a {current_stop_loss:.2f}.",
            "stopped": "{symbol} {direction}: stop alcanzado en {current_stop_loss:.2f}.",
            "invalidated": "{symbol} {direction}: trade invalidado. Revisa el setup.",
        },
    }
    language_normalized = language if language in templates else "en"
    template = templates[language_normalized][event_type]
    return template.format(
        symbol=symbol,
        direction=direction,
        current_price=current_price,
        previous_stop_loss=float(previous_stop_loss) if previous_stop_loss is not None else 0.0,
        current_stop_loss=float(current_stop_loss) if current_stop_loss is not None else 0.0,
        reference_price=float(reference_price) if reference_price is not None else current_price,
    )


def _build_trade_management_event_key(user_id: int, event: dict[str, Any]) -> str:
    payload = {
        "user_id": user_id,
        "symbol": event["symbol"],
        "event_type": event["event_type"],
        "direction": event["direction"],
        "status": event["status"],
        "current_price": round(float(event["current_price"]), 8),
        "previous_stop_loss": round(float(event["previous_stop_loss"]), 8) if event.get("previous_stop_loss") is not None else None,
        "current_stop_loss": round(float(event["current_stop_loss"]), 8) if event.get("current_stop_loss") is not None else None,
        "reference_price": round(float(event["reference_price"]), 8) if event.get("reference_price") is not None else None,
        "detail": event.get("detail"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:24]


def save_trade_event(event: dict[str, Any]) -> dict[str, Any]:
    record = {
        "id": str(event.get("id") or str(uuid.uuid4())),
        "trade_id": event.get("trade_id"),
        "user_id": int(event["user_id"]),
        "event_type": str(event["event_type"]),
        "message": str(event["message"]),
        "created_at": str(event.get("created_at") or _format_utc_timestamp(time.time())),
        "acknowledged": 1 if bool(event.get("acknowledged", False)) else 0,
    }

    with closing(get_connection()) as connection:
        connection.execute(
            """
            INSERT INTO trade_events (
                id,
                trade_id,
                user_id,
                event_type,
                message,
                created_at,
                acknowledged
            )
            VALUES (
                :id,
                :trade_id,
                :user_id,
                :event_type,
                :message,
                :created_at,
                :acknowledged
            )
            ON CONFLICT(id) DO UPDATE SET
                trade_id = excluded.trade_id,
                user_id = excluded.user_id,
                event_type = excluded.event_type,
                message = excluded.message,
                created_at = excluded.created_at,
                acknowledged = excluded.acknowledged
            """,
            record,
        )
        connection.commit()

    persisted = dict(record)
    persisted["acknowledged"] = bool(persisted["acknowledged"])
    return persisted


def get_pending_trade_events(user_id: int | None = None, acknowledged: bool | None = False) -> list[dict[str, Any]]:
    query = """
        SELECT id, trade_id, user_id, event_type, message, created_at, acknowledged
        FROM trade_events
        WHERE 1 = 1
    """
    params: list[Any] = []
    if acknowledged is not None:
        query += " AND acknowledged = ?"
        params.append(1 if acknowledged else 0)
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    query += " ORDER BY created_at ASC, id ASC"

    with closing(get_connection()) as connection:
        rows = connection.execute(query, tuple(params)).fetchall()

    return [row_to_trade_event_record(row) for row in rows]


def acknowledge_trade_event(event_id: str) -> None:
    with closing(get_connection()) as connection:
        connection.execute(
            """
            UPDATE trade_events
            SET acknowledged = 1
            WHERE id = ?
            """,
            (event_id,),
        )
        connection.commit()


def _enqueue_trade_management_jobs(
    user_id: int,
    events: list[dict[str, Any]],
    *,
    language: str | None,
    level: str | None,
) -> list[dict[str, Any]]:
    jobs = _TRADE_MANAGEMENT_JOB_QUEUE.setdefault(user_id, {})
    created_at = _format_utc_timestamp(time.time())
    queued_jobs: list[dict[str, Any]] = []

    for event in events:
        event_key = _build_trade_management_event_key(user_id, event)
        if event_key in jobs:
            queued_jobs.append(jobs[event_key])
            continue

        message = format_trade_management_event_message(event, language or "en")
        if level == "medium" and event.get("detail"):
            message = f"{message}\n{event['detail']}"
        if level == "pro":
            extra_lines = []
            if event.get("previous_stop_loss") is not None and event.get("current_stop_loss") is not None:
                extra_lines.append(
                    f"SL: {float(event['previous_stop_loss']):.2f} -> {float(event['current_stop_loss']):.2f}"
                )
            extra_lines.append(f"Price: {float(event['current_price']):.2f}")
            message = "\n".join([message, *extra_lines])

        job = {
            "user_id": user_id,
            "language": language,
            "level": level,
            "event_key": event_key,
            "trade_id": event.get("trade_id"),
            "event_type": event["event_type"],
            "symbol": event["symbol"],
            "message": message,
            "current_price": float(event["current_price"]),
            "created_at": created_at,
        }
        jobs[event_key] = job
        save_trade_event(
            {
                "id": event_key,
                "trade_id": event.get("trade_id"),
                "user_id": user_id,
                "event_type": event["event_type"],
                "message": message,
                "created_at": created_at,
                "acknowledged": False,
            }
        )
        queued_jobs.append(job)

    return queued_jobs


def simulate_trade_management(
    user_id: int,
    previous_plan: Any,
    current_plan: Any,
    current_price: float,
    *,
    trade_id: str | None = None,
    invalidated: bool = False,
) -> list[dict[str, Any]]:
    user = get_user(user_id)
    events = detect_trade_management_events(
        previous_plan,
        current_plan,
        current_price,
        invalidated=invalidated,
    )
    if not events:
        return []

    if trade_id:
        events = [{**event, "trade_id": trade_id} for event in events]

    return _enqueue_trade_management_jobs(
        user_id,
        events,
        language=user.get("language"),
        level=user.get("level"),
    )


def get_trade_management_jobs() -> list[dict[str, Any]]:
    jobs_by_key: dict[str, dict[str, Any]] = {}
    for user_jobs in _TRADE_MANAGEMENT_JOB_QUEUE.values():
        for event_key, job in user_jobs.items():
            jobs_by_key[event_key] = job

    for event in get_pending_trade_events():
        event_key = event["id"]
        if event_key in jobs_by_key:
            continue
        jobs_by_key[event_key] = {
            "user_id": event["user_id"],
            "language": None,
            "level": None,
            "event_key": event_key,
            "trade_id": event.get("trade_id"),
            "event_type": event["event_type"],
            "symbol": "",
            "message": event["message"],
            "current_price": 0.0,
            "created_at": event["created_at"],
        }

    return sorted(jobs_by_key.values(), key=lambda item: (item["created_at"], item["user_id"], item["event_key"]))


def acknowledge_trade_management_event(user_id: int, event_key: str) -> None:
    user_jobs = _TRADE_MANAGEMENT_JOB_QUEUE.get(user_id)
    if user_jobs:
        user_jobs.pop(event_key, None)
        if not user_jobs:
            _TRADE_MANAGEMENT_JOB_QUEUE.pop(user_id, None)
    acknowledge_trade_event(event_key)


def _normalize_archetype(archetype: str | None) -> str:
    return " ".join(str(archetype or "").strip().lower().split())


def calculate_trade_journal_stats(entries: list[Any]) -> dict[str, Any]:
    normalized_entries = list(entries or [])
    if not normalized_entries:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "average_r_multiple": 0.0,
            "average_tp_hit_count": 0.0,
            "stopped_after_tp_rate": 0.0,
            "performance_by_archetype": {},
        }

    total_trades = len(normalized_entries)
    positive_r_wins_count = 0  # Win rate intentionally counts only trades with realized_r_multiple > 0.
    total_r_multiple = 0.0
    total_tp_hit_count = 0
    stopped_after_tp_count = 0  # Rate remains measured over total_trades, not only trades that reached TP.
    by_archetype: dict[str, dict[str, float]] = {}

    for entry in normalized_entries:
        archetype = _normalize_archetype(entry["archetype"] if isinstance(entry, dict) else entry.archetype)
        realized_r_multiple = float(entry["realized_r_multiple"] if isinstance(entry, dict) else entry.realized_r_multiple)
        tp_hit_count = int(entry["tp_hit_count"] if isinstance(entry, dict) else entry.tp_hit_count)
        stopped_after_tp = bool(entry["stopped_after_tp"] if isinstance(entry, dict) else entry.stopped_after_tp)

        positive_r_wins_count += 1 if realized_r_multiple > 0 else 0
        total_r_multiple += realized_r_multiple
        total_tp_hit_count += tp_hit_count
        stopped_after_tp_count += 1 if stopped_after_tp else 0

        bucket = by_archetype.setdefault(
            archetype,
            {"total_trades": 0.0, "wins": 0.0, "total_r_multiple": 0.0},
        )
        bucket["total_trades"] += 1.0
        bucket["wins"] += 1.0 if realized_r_multiple > 0 else 0.0
        bucket["total_r_multiple"] += realized_r_multiple

    performance_by_archetype = {
        archetype: {
            "total_trades": int(values["total_trades"]),
            "win_rate": values["wins"] / values["total_trades"] if values["total_trades"] else 0.0,
            "average_r_multiple": values["total_r_multiple"] / values["total_trades"] if values["total_trades"] else 0.0,
        }
        for archetype, values in by_archetype.items()
    }

    return {
        "total_trades": total_trades,
        "win_rate": positive_r_wins_count / total_trades,
        "average_r_multiple": total_r_multiple / total_trades,
        "average_tp_hit_count": total_tp_hit_count / total_trades,
        "stopped_after_tp_rate": stopped_after_tp_count / total_trades,
        "performance_by_archetype": performance_by_archetype,
    }


def _validate_feedback_label(label: str | None) -> str | None:
    if label is None:
        return None
    normalized_label = str(label).strip().lower()
    if normalized_label not in {"good", "neutral", "bad"}:
        raise ValueError("feedback_label must be 'good', 'neutral', or 'bad'.")
    return normalized_label


def _feedback_label_weight(label: str | None) -> float:
    normalized_label = _validate_feedback_label(label)
    return {
        "good": 1.0,
        "neutral": 0.0,
        "bad": -1.0,
    }.get(normalized_label or "", 0.0)


def adaptive_setup_score_adjustment(
    base_score: float,
    archetype: str,
    journal_entries: list[Any] | None = None,
    feedback_label: str | None = None,
    noise_score: float = 0.0,
) -> float:
    adjusted_score = float(base_score)
    normalized_archetype = _normalize_archetype(archetype)
    normalized_feedback_label = _validate_feedback_label(feedback_label)
    relevant_entries = [
        entry
        for entry in (journal_entries or [])
        if _normalize_archetype(entry["archetype"] if isinstance(entry, dict) else entry.archetype) == normalized_archetype
    ]

    archetype_stats = calculate_trade_journal_stats(relevant_entries)
    performance = archetype_stats["performance_by_archetype"].get(normalized_archetype)
    if performance:
        win_rate_adjustment = (float(performance["win_rate"]) - 0.5) * 10.0
        average_r_adjustment = max(-4.0, min(4.0, float(performance["average_r_multiple"]) * 2.0))
        sample_size = int(performance["total_trades"])
        sample_weight = min(1.0, sample_size / 5.0) ** 2
        adjusted_score += (win_rate_adjustment + average_r_adjustment) * sample_weight

    recent_feedback_entries = relevant_entries[-3:]
    recent_feedback_values = [
        _feedback_label_weight(entry["feedback_label"] if isinstance(entry, dict) else entry.feedback_label)
        for entry in recent_feedback_entries
    ]
    if recent_feedback_values:
        adjusted_score += (sum(recent_feedback_values) / len(recent_feedback_values)) * 2.0

    adjusted_score += _feedback_label_weight(normalized_feedback_label) * 1.5

    noise_penalty = max(0.0, float(noise_score) - 50.0) / 12.5
    adjusted_score -= min(6.0, noise_penalty)

    return float(max(0.0, min(100.0, adjusted_score)))


def _get_user_watchlist(user: dict[str, Any]) -> list[str]:
    watchlist = _normalize_coin_list(user.get("coins"))
    if watchlist:
        return watchlist
    return DEFAULT_MARKET_COINS.copy()


def _get_scanner_universe(user: dict[str, Any]) -> list[str]:
    return _normalize_coin_list([*_get_user_watchlist(user), *SCANNER_DISCOVERY_COINS])


def _get_effective_scanner_limit(user: dict[str, Any]) -> int:
    level = user.get("level")
    if level == "beginner":
        return MIN_SCANNER_LIMIT
    if level == "medium":
        return MEDIUM_SCANNER_LIMIT

    configured_limit = user.get("scanner_limit")
    if isinstance(configured_limit, int):
        return max(MIN_SCANNER_LIMIT, min(configured_limit, MAX_SCANNER_LIMIT))
    return MAX_SCANNER_LIMIT


def _get_effective_signal_limit(user: dict[str, Any]) -> int:
    level = user.get("level")
    if level == "beginner":
        return 1
    if level == "medium":
        return 3
    return MAX_SCANNER_LIMIT


def _get_effective_alerts_min_priority(user: dict[str, Any]) -> str:
    level = user.get("level")
    if level == "beginner":
        return "high"
    if level == "medium":
        return "medium"

    configured_priority = user.get("alerts_min_priority")
    if configured_priority in ALERT_PRIORITIES:
        return configured_priority
    return "high"


def _get_signal_level_profile(level: str | None) -> dict[str, Any]:
    if level == "beginner":
        return {
            "label": "beginner",
            "checklist": [
                "Keep one clear setup in focus.",
                "Wait for confirmation before acting.",
                "Ignore weaker names until structure improves.",
            ],
        }
    if level == "medium":
        return {
            "label": "medium",
            "checklist": [
                "Use trigger, size, and invalidation together before taking risk.",
                "Focus on Active first, then Watch setups with clean reclaim logic.",
                "Reduce size quickly when volatility expands.",
            ],
        }
    return {
        "label": "pro",
        "checklist": [
            "Act only on setups marked Active after confirmation, never before it.",
            "Use the trigger line to decide entry and the size plan to control exposure.",
            "Skip Stand aside names until both structure and momentum improve together.",
        ],
    }


def ensure_database_schema() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                intro_seen INTEGER NOT NULL DEFAULT 0,
                language TEXT,
                level TEXT,
                scanner_limit INTEGER,
                market TEXT,
                trading_style TEXT,
                coins TEXT NOT NULL DEFAULT '[]',
                alerts_enabled INTEGER NOT NULL DEFAULT 0,
                alerts_min_priority TEXT NOT NULL DEFAULT 'high',
                last_alert_digest TEXT,
                last_alert_sent_at TEXT,
                onboarding_complete INTEGER NOT NULL DEFAULT 0,
                active_message_id INTEGER
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_plans (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                initial_stop_loss REAL NOT NULL,
                current_stop_loss REAL NOT NULL,
                tp1 REAL,
                tp2 REAL,
                tpf REAL,
                status TEXT NOT NULL,
                risk_percent REAL NOT NULL,
                initial_risk_percent REAL NOT NULL,
                risk_percent_per_trade REAL NOT NULL DEFAULT 0,
                risk_amount REAL NOT NULL DEFAULT 0,
                position_size REAL NOT NULL DEFAULT 0,
                unrealized_r_multiple REAL NOT NULL DEFAULT 0,
                realized_r_multiple REAL NOT NULL DEFAULT 0,
                tp_hit_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(TRADE_JOURNAL_TABLE_SQL)
        connection.execute(TRADE_EVENTS_TABLE_SQL)

        columns = {row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()}

        if "intro_seen" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN intro_seen INTEGER NOT NULL DEFAULT 0")
        if "level" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN level TEXT")
        if "scanner_limit" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN scanner_limit INTEGER")
        if "alerts_enabled" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN alerts_enabled INTEGER NOT NULL DEFAULT 0")
        if "alerts_min_priority" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN alerts_min_priority TEXT NOT NULL DEFAULT 'high'")
        if "last_alert_digest" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_alert_digest TEXT")
        if "last_alert_sent_at" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_alert_sent_at TEXT")

        trade_plan_columns = {row[1] for row in connection.execute("PRAGMA table_info(trade_plans)").fetchall()}
        if "risk_percent_per_trade" not in trade_plan_columns:
            connection.execute("ALTER TABLE trade_plans ADD COLUMN risk_percent_per_trade REAL NOT NULL DEFAULT 0")
        if "risk_amount" not in trade_plan_columns:
            connection.execute("ALTER TABLE trade_plans ADD COLUMN risk_amount REAL NOT NULL DEFAULT 0")
        if "position_size" not in trade_plan_columns:
            connection.execute("ALTER TABLE trade_plans ADD COLUMN position_size REAL NOT NULL DEFAULT 0")
        if "unrealized_r_multiple" not in trade_plan_columns:
            connection.execute("ALTER TABLE trade_plans ADD COLUMN unrealized_r_multiple REAL NOT NULL DEFAULT 0")
        if "realized_r_multiple" not in trade_plan_columns:
            connection.execute("ALTER TABLE trade_plans ADD COLUMN realized_r_multiple REAL NOT NULL DEFAULT 0")

        connection.commit()


def get_connection() -> sqlite3.Connection:
    ensure_database_schema()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _trade_plan_value(trade_plan: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(trade_plan, dict):
        return trade_plan.get(field_name, default)
    return getattr(trade_plan, field_name, default)


def _row_to_trade_plan_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": int(row["user_id"]),
        "symbol": row["symbol"],
        "direction": row["direction"],
        "entry_price": float(row["entry_price"]),
        "initial_stop_loss": float(row["initial_stop_loss"]),
        "current_stop_loss": float(row["current_stop_loss"]),
        "tp1": float(row["tp1"]) if row["tp1"] is not None else None,
        "tp2": float(row["tp2"]) if row["tp2"] is not None else None,
        "tpf": float(row["tpf"]) if row["tpf"] is not None else None,
        "status": row["status"],
        "risk_percent": float(row["risk_percent"]),
        "initial_risk_percent": float(row["initial_risk_percent"]),
        "risk_percent_per_trade": float(row["risk_percent_per_trade"]) if row["risk_percent_per_trade"] is not None else 0.0,
        "risk_amount": float(row["risk_amount"]) if row["risk_amount"] is not None else 0.0,
        "position_size": float(row["position_size"]) if row["position_size"] is not None else 0.0,
        "unrealized_r_multiple": float(row["unrealized_r_multiple"]) if row["unrealized_r_multiple"] is not None else 0.0,
        "realized_r_multiple": float(row["realized_r_multiple"]) if row["realized_r_multiple"] is not None else 0.0,
        "tp_hit_count": int(row["tp_hit_count"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _build_trade_plan_record(user_id: int, trade_plan: Any, trade_id: str | None = None) -> dict[str, Any]:
    created_at = _trade_plan_value(trade_plan, "created_at") or _format_utc_timestamp(time.time())
    updated_at = _trade_plan_value(trade_plan, "updated_at") or created_at
    return {
        "id": trade_id or str(uuid.uuid4()),
        "user_id": user_id,
        "symbol": _trade_plan_value(trade_plan, "symbol"),
        "direction": _trade_plan_value(trade_plan, "direction"),
        "entry_price": _trade_plan_value(trade_plan, "entry_price"),
        "initial_stop_loss": _trade_plan_value(trade_plan, "initial_stop_loss"),
        "current_stop_loss": _trade_plan_value(trade_plan, "current_stop_loss"),
        "tp1": _trade_plan_value(trade_plan, "tp1"),
        "tp2": _trade_plan_value(trade_plan, "tp2"),
        "tpf": _trade_plan_value(trade_plan, "tpf"),
        "status": _trade_plan_value(trade_plan, "status"),
        "risk_percent": _trade_plan_value(trade_plan, "risk_percent"),
        "initial_risk_percent": _trade_plan_value(trade_plan, "initial_risk_percent"),
        "risk_percent_per_trade": _trade_plan_value(trade_plan, "risk_percent_per_trade", 0.0),
        "risk_amount": _trade_plan_value(trade_plan, "risk_amount", 0.0),
        "position_size": _trade_plan_value(trade_plan, "position_size", 0.0),
        "unrealized_r_multiple": _trade_plan_value(trade_plan, "unrealized_r_multiple", 0.0),
        "realized_r_multiple": _trade_plan_value(trade_plan, "realized_r_multiple", 0.0),
        "tp_hit_count": int(_trade_plan_value(trade_plan, "tp_hit_count", 0) or 0),
        "created_at": created_at,
        "updated_at": updated_at,
    }


def _trade_journal_entry_value(entry: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(entry, dict):
        return entry.get(field_name, default)
    return getattr(entry, field_name, default)


def _build_trade_journal_record(user_id: int, entry: Any) -> dict[str, Any]:
    status = _trade_journal_entry_value(entry, "status")
    if status is not None and status != "closed":
        raise ValueError("Only closed trade journal entries can be persisted.")

    trade_id = _trade_journal_entry_value(entry, "trade_id") or str(uuid.uuid4())
    exit_price = _trade_journal_entry_value(entry, "exit_price")
    exit_reason = _trade_journal_entry_value(entry, "exit_reason")
    closed_at = _trade_journal_entry_value(entry, "closed_at")
    if exit_price is None or exit_reason is None or closed_at is None:
        raise ValueError("Closed trade journal entries require exit_price, exit_reason, and closed_at.")

    return {
        "trade_id": trade_id,
        "user_id": user_id,
        "symbol": _trade_journal_entry_value(entry, "symbol"),
        "direction": _trade_journal_entry_value(entry, "direction"),
        "archetype": _trade_journal_entry_value(entry, "archetype"),
        "entry_price": _trade_journal_entry_value(entry, "entry_price"),
        "initial_stop_loss": _trade_journal_entry_value(entry, "initial_stop_loss"),
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "realized_r_multiple": _trade_journal_entry_value(entry, "realized_r_multiple"),
        "tp_hit_count": int(_trade_journal_entry_value(entry, "tp_hit_count", 0) or 0),
        "stopped_after_tp": 1 if _trade_journal_entry_value(entry, "stopped_after_tp", False) else 0,
        "feedback_label": _trade_journal_entry_value(entry, "feedback_label"),
        "created_at": _trade_journal_entry_value(entry, "created_at"),
        "closed_at": closed_at,
    }


def get_default_user(user_id: int) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "intro_seen": False,
        "language": None,
        "level": None,
        "scanner_limit": None,
        "market": None,
        "trading_style": None,
        "coins": [],
        "alerts_enabled": False,
        "alerts_min_priority": "high",
        "last_alert_digest": None,
        "last_alert_sent_at": None,
        "onboarding_complete": False,
        "active_message_id": None,
    }


def compute_onboarding_complete(user: dict[str, Any]) -> bool:
    return bool(
        user.get("language")
        and user.get("level")
        and user.get("market")
        and user.get("trading_style")
        and isinstance(user.get("coins"), list)
        and len(user["coins"]) == 3
    )


def get_next_step(user: dict[str, Any]) -> str:
    if not user.get("intro_seen"):
        return "intro"
    if not user.get("language"):
        return "language"
    if not user.get("level"):
        return "level"
    if not user.get("market"):
        return "market"
    if not user.get("trading_style"):
        return "style"
    if len(user.get("coins", [])) != 3:
        return "coins"
    return "welcome"


def _parse_coins(raw_coins: str | None) -> list[str]:
    if not raw_coins:
        return []

    try:
        parsed = json.loads(raw_coins)
    except json.JSONDecodeError:
        return []

    return parsed if isinstance(parsed, list) else []


def _serialize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": user["user_id"],
        "intro_seen": 1 if user.get("intro_seen") else 0,
        "language": user.get("language"),
        "level": user.get("level"),
        "scanner_limit": user.get("scanner_limit"),
        "market": user.get("market"),
        "trading_style": user.get("trading_style"),
        "coins": json.dumps(user.get("coins", [])),
        "alerts_enabled": 1 if user.get("alerts_enabled") else 0,
        "alerts_min_priority": user.get("alerts_min_priority", "high"),
        "last_alert_digest": user.get("last_alert_digest"),
        "last_alert_sent_at": user.get("last_alert_sent_at"),
        "onboarding_complete": 1 if user.get("onboarding_complete") else 0,
        "active_message_id": user.get("active_message_id"),
    }


def _row_to_user(row: sqlite3.Row | None, user_id: int) -> dict[str, Any]:
    if row is None:
        user = get_default_user(user_id)
    else:
        user = {
            "user_id": row["user_id"],
            "intro_seen": bool(row["intro_seen"]),
            "language": row["language"],
            "level": row["level"],
            "scanner_limit": row["scanner_limit"],
            "market": row["market"],
            "trading_style": row["trading_style"],
            "coins": _parse_coins(row["coins"]),
            "alerts_enabled": bool(row["alerts_enabled"]),
            "alerts_min_priority": row["alerts_min_priority"] or "high",
            "last_alert_digest": row["last_alert_digest"],
            "last_alert_sent_at": row["last_alert_sent_at"],
            "onboarding_complete": bool(row["onboarding_complete"]),
            "active_message_id": row["active_message_id"],
        }

    user["onboarding_complete"] = compute_onboarding_complete(user)
    user["next_step"] = get_next_step(user)
    return user


def get_user(user_id: int) -> dict[str, Any]:
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT user_id, intro_seen, language, level, scanner_limit, market, trading_style, coins, alerts_enabled, alerts_min_priority, last_alert_digest, last_alert_sent_at, onboarding_complete, active_message_id
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return _row_to_user(row, user_id)


def _validate_partial_user(data: dict[str, Any]) -> None:
    language = data.get("language")
    level = data.get("level")
    scanner_limit = data.get("scanner_limit")
    market = data.get("market")
    trading_style = data.get("trading_style")
    coins = data.get("coins", [])
    alerts_min_priority = data.get("alerts_min_priority")

    if language is not None and language not in ALLOWED_LANGUAGES:
        raise ValueError("Unsupported language.")
    if level is not None and level not in ALLOWED_LEVELS:
        raise ValueError("Unsupported experience level.")
    if scanner_limit is not None and (
        not isinstance(scanner_limit, int) or scanner_limit < MIN_SCANNER_LIMIT or scanner_limit > MAX_SCANNER_LIMIT
    ):
        raise ValueError(f"Scanner limit must be between {MIN_SCANNER_LIMIT} and {MAX_SCANNER_LIMIT}.")
    if market is not None and market not in ALLOWED_MARKETS:
        raise ValueError("Unsupported market.")
    if trading_style is not None and trading_style not in ALLOWED_TRADING_STYLES:
        raise ValueError("Unsupported trading style.")
    if not isinstance(coins, list):
        raise ValueError("Coins must be a list.")
    if len(coins) > 3:
        raise ValueError("Coins can contain at most 3 symbols.")
    if alerts_min_priority is not None and alerts_min_priority not in ALERT_PRIORITIES:
        raise ValueError("Unsupported alerts priority.")


def save_user(user_id: int, patch: dict[str, Any]) -> dict[str, Any]:
    user = get_user(user_id)

    allowed_fields = {
        "intro_seen",
        "language",
        "level",
        "scanner_limit",
        "market",
        "trading_style",
        "coins",
        "alerts_enabled",
        "alerts_min_priority",
        "active_message_id",
    }

    for field_name in allowed_fields:
        if field_name in patch:
            user[field_name] = patch[field_name]

    if user.get("level") == "beginner":
        user["scanner_limit"] = MIN_SCANNER_LIMIT
        user["alerts_min_priority"] = "high"
    elif user.get("level") == "medium":
        user["scanner_limit"] = MEDIUM_SCANNER_LIMIT
        user["alerts_min_priority"] = "medium"
    elif user.get("level") == "pro" and not isinstance(user.get("scanner_limit"), int):
        user["scanner_limit"] = MAX_SCANNER_LIMIT

    user["user_id"] = user_id
    _validate_partial_user(user)
    user["onboarding_complete"] = compute_onboarding_complete(user)

    with closing(get_connection()) as connection:
        connection.execute(
            """
            INSERT INTO users (
                user_id,
                intro_seen,
                language,
                level,
                scanner_limit,
                market,
                trading_style,
                coins,
                alerts_enabled,
                alerts_min_priority,
                last_alert_digest,
                last_alert_sent_at,
                onboarding_complete,
                active_message_id
            )
            VALUES (
                :user_id,
                :intro_seen,
                :language,
                :level,
                :scanner_limit,
                :market,
                :trading_style,
                :coins,
                :alerts_enabled,
                :alerts_min_priority,
                :last_alert_digest,
                :last_alert_sent_at,
                :onboarding_complete,
                :active_message_id
            )
            ON CONFLICT(user_id) DO UPDATE SET
                intro_seen = excluded.intro_seen,
                language = excluded.language,
                level = excluded.level,
                scanner_limit = excluded.scanner_limit,
                market = excluded.market,
                trading_style = excluded.trading_style,
                coins = excluded.coins,
                alerts_enabled = excluded.alerts_enabled,
                alerts_min_priority = excluded.alerts_min_priority,
                last_alert_digest = excluded.last_alert_digest,
                last_alert_sent_at = excluded.last_alert_sent_at,
                onboarding_complete = excluded.onboarding_complete,
                active_message_id = excluded.active_message_id
            """,
            _serialize_user(user),
        )
        connection.commit()

    return get_user(user_id)


def save_trade_plan(user_id: int, trade_plan: Any) -> dict[str, Any]:
    record = _build_trade_plan_record(user_id, trade_plan)

    with closing(get_connection()) as connection:
        connection.execute(
            """
            INSERT INTO trade_plans (
                id,
                user_id,
                symbol,
                direction,
                entry_price,
                initial_stop_loss,
                current_stop_loss,
                tp1,
                tp2,
                tpf,
                status,
                risk_percent,
                initial_risk_percent,
                risk_percent_per_trade,
                risk_amount,
                position_size,
                unrealized_r_multiple,
                realized_r_multiple,
                tp_hit_count,
                created_at,
                updated_at
            )
            VALUES (
                :id,
                :user_id,
                :symbol,
                :direction,
                :entry_price,
                :initial_stop_loss,
                :current_stop_loss,
                :tp1,
                :tp2,
                :tpf,
                :status,
                :risk_percent,
                :initial_risk_percent,
                :risk_percent_per_trade,
                :risk_amount,
                :position_size,
                :unrealized_r_multiple,
                :realized_r_multiple,
                :tp_hit_count,
                :created_at,
                :updated_at
            )
            """,
            record,
        )
        connection.commit()

    return record


def get_trade_plans_by_user(user_id: int) -> list[dict[str, Any]]:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                user_id,
                symbol,
                direction,
                entry_price,
                initial_stop_loss,
                current_stop_loss,
                tp1,
                tp2,
                tpf,
                status,
                risk_percent,
                initial_risk_percent,
                risk_percent_per_trade,
                risk_amount,
                position_size,
                unrealized_r_multiple,
                realized_r_multiple,
                tp_hit_count,
                created_at,
                updated_at
            FROM trade_plans
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()

    return [_row_to_trade_plan_record(row) for row in rows]


def update_trade_plan(trade_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    allowed_fields = {
        "symbol",
        "direction",
        "entry_price",
        "initial_stop_loss",
        "current_stop_loss",
        "tp1",
        "tp2",
        "tpf",
        "status",
        "risk_percent",
        "initial_risk_percent",
        "risk_percent_per_trade",
        "risk_amount",
        "position_size",
        "unrealized_r_multiple",
        "realized_r_multiple",
        "tp_hit_count",
    }

    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                id,
                user_id,
                symbol,
                direction,
                entry_price,
                initial_stop_loss,
                current_stop_loss,
                tp1,
                tp2,
                tpf,
                status,
                risk_percent,
                initial_risk_percent,
                risk_percent_per_trade,
                risk_amount,
                position_size,
                unrealized_r_multiple,
                realized_r_multiple,
                tp_hit_count,
                created_at,
                updated_at
            FROM trade_plans
            WHERE id = ?
            """,
            (trade_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Trade plan not found.")

        record = _row_to_trade_plan_record(row)
        for field_name in allowed_fields:
            if field_name in patch:
                record[field_name] = patch[field_name]
        record["updated_at"] = _format_utc_timestamp(time.time())

        connection.execute(
            """
            UPDATE trade_plans
            SET
                symbol = :symbol,
                direction = :direction,
                entry_price = :entry_price,
                initial_stop_loss = :initial_stop_loss,
                current_stop_loss = :current_stop_loss,
                tp1 = :tp1,
                tp2 = :tp2,
                tpf = :tpf,
                status = :status,
                risk_percent = :risk_percent,
                initial_risk_percent = :initial_risk_percent,
                risk_percent_per_trade = :risk_percent_per_trade,
                risk_amount = :risk_amount,
                position_size = :position_size,
                unrealized_r_multiple = :unrealized_r_multiple,
                realized_r_multiple = :realized_r_multiple,
                tp_hit_count = :tp_hit_count,
                updated_at = :updated_at
            WHERE id = :id
            """,
            record,
        )
        connection.commit()

    return record


def save_trade_journal_entry(user_id: int, entry: Any) -> dict[str, Any]:
    record = _build_trade_journal_record(user_id, entry)

    with closing(get_connection()) as connection:
        connection.execute(
            """
            INSERT INTO trade_journal (
                trade_id,
                user_id,
                symbol,
                direction,
                archetype,
                entry_price,
                initial_stop_loss,
                exit_price,
                exit_reason,
                realized_r_multiple,
                tp_hit_count,
                stopped_after_tp,
                feedback_label,
                created_at,
                closed_at
            )
            VALUES (
                :trade_id,
                :user_id,
                :symbol,
                :direction,
                :archetype,
                :entry_price,
                :initial_stop_loss,
                :exit_price,
                :exit_reason,
                :realized_r_multiple,
                :tp_hit_count,
                :stopped_after_tp,
                :feedback_label,
                :created_at,
                :closed_at
            )
            """,
            record,
        )
        connection.commit()

    persisted_record = dict(record)
    persisted_record["stopped_after_tp"] = bool(persisted_record["stopped_after_tp"])
    return persisted_record


def get_trade_journal_by_user(user_id: int) -> list[dict[str, Any]]:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                trade_id,
                user_id,
                symbol,
                direction,
                archetype,
                entry_price,
                initial_stop_loss,
                exit_price,
                exit_reason,
                realized_r_multiple,
                tp_hit_count,
                stopped_after_tp,
                feedback_label,
                created_at,
                closed_at
            FROM trade_journal
            WHERE user_id = ?
            ORDER BY closed_at DESC, trade_id DESC
            """,
            (user_id,),
        ).fetchall()

    return [row_to_trade_journal_record(row) for row in rows]


def reset_user(user_id: int, keep_intro_seen: bool = True) -> dict[str, Any]:
    existing_user = get_user(user_id)
    user = get_default_user(user_id)
    user["intro_seen"] = existing_user["intro_seen"] if keep_intro_seen else False
    user["active_message_id"] = existing_user["active_message_id"]
    return save_user(user_id, user)


def _clamp_int(value: float, minimum: int = 1, maximum: int = 99) -> int:
    return max(minimum, min(maximum, int(round(value))))


def _format_live_symbol(symbol: str) -> str:
    return BINANCE_SYMBOL_MAP.get(symbol, f"{symbol}USDT")


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _score_risk_posture(volatility_label: str, market_type: str, trading_style: str) -> str:
    if market_type == "futures" and trading_style == "scalping":
        if volatility_label == "Explosive":
            return "Reduced size until momentum confirms clean continuation."
        return "Trade only confirmed breaks and avoid late entries."
    if volatility_label == "Explosive":
        return "Reduced size until momentum confirms clean continuation."
    if volatility_label == "Active":
        return "Trade only confirmed breaks and avoid late entries."
    return "Normal risk is acceptable, but only with structure in your favor."


def _get_strategy_profile(market_type: str, trading_style: str) -> dict[str, float]:
    profile = {
        "trigger_floor_adjustment": 0.0,
        "quality_floor_adjustment": 0.0,
        "noise_cap_adjustment": 0.0,
        "distance_weight": 1.0,
        "watchlist_bonus": 4.0,
        "high_alert_trigger_floor": 78.0,
        "high_alert_quality_floor": 74.0,
        "high_alert_noise_cap": 42.0,
        "medium_alert_trigger_floor": 68.0,
        "medium_alert_quality_floor": 64.0,
        "medium_alert_noise_cap": 52.0,
        "scanner_filter_floor": 64.0,
    }

    if market_type == "futures":
        profile["trigger_floor_adjustment"] += 3.0
        profile["quality_floor_adjustment"] += 2.0
        profile["noise_cap_adjustment"] -= 3.0
        profile["distance_weight"] += 0.10
        profile["watchlist_bonus"] = 3.0
        profile["high_alert_trigger_floor"] += 2.0
        profile["high_alert_quality_floor"] += 2.0
        profile["high_alert_noise_cap"] -= 2.0
        profile["medium_alert_trigger_floor"] += 2.0
        profile["medium_alert_quality_floor"] += 1.0
        profile["medium_alert_noise_cap"] -= 2.0
        profile["scanner_filter_floor"] += 3.0

    if trading_style == "scalping":
        profile["trigger_floor_adjustment"] += 3.0
        profile["quality_floor_adjustment"] += 1.0
        profile["noise_cap_adjustment"] -= 4.0
        profile["distance_weight"] += 0.18
        profile["watchlist_bonus"] -= 1.0
        profile["high_alert_trigger_floor"] += 2.0
        profile["high_alert_quality_floor"] += 1.0
        profile["high_alert_noise_cap"] -= 2.0
        profile["medium_alert_trigger_floor"] += 1.0
        profile["medium_alert_noise_cap"] -= 2.0
        profile["scanner_filter_floor"] += 2.0

    if market_type == "spot" and trading_style == "intraday":
        profile["quality_floor_adjustment"] -= 1.0
        profile["noise_cap_adjustment"] += 2.0
        profile["distance_weight"] -= 0.06
        profile["watchlist_bonus"] += 1.0
        profile["medium_alert_noise_cap"] += 2.0

    return profile


def _classify_market_asset(
    pulse_score: int,
    breakout_score: int,
    coin_volatility: int,
    market_type: str,
    trading_style: str,
    price_change_percent: float | None = None,
) -> tuple[str, str, str]:
    ready_breakout_floor = 68
    ready_pulse_floor = 72
    watch_breakout_floor = 56
    watch_pulse_floor = 60
    cooldown_floor = 46

    if market_type == "futures":
        ready_breakout_floor += 4
        ready_pulse_floor += 2
        watch_breakout_floor += 2
        watch_pulse_floor += 1
    if trading_style == "scalping":
        ready_breakout_floor += 3
        ready_pulse_floor += 1
        watch_breakout_floor += 2
        cooldown_floor += 2

    if pulse_score >= ready_pulse_floor and breakout_score >= ready_breakout_floor:
        bias = "Long bias"
        setup = "Trend continuation"
        signal = "Ready"
    elif pulse_score >= watch_pulse_floor and breakout_score >= watch_breakout_floor:
        bias = "Watch for reclaim"
        setup = "Breakout watch"
        signal = "Watch"
    elif max(pulse_score, breakout_score) >= cooldown_floor:
        bias = "Wait"
        setup = "Session range" if trading_style == "intraday" else "Range / reset"
        signal = "Watch"
    else:
        bias = "Wait"
        setup = "Range / reset"
        signal = "Cool-off"

    if market_type == "futures":
        if coin_volatility >= (74 if trading_style == "scalping" else 78):
            setup = "Fast momentum"
            if breakout_score < ready_breakout_floor or pulse_score < ready_pulse_floor:
                signal = "Watch" if max(pulse_score, breakout_score) >= watch_breakout_floor else "Cool-off"
                bias = "Watch for reclaim" if signal == "Watch" else "Wait"
        elif signal == "Watch" and breakout_score < watch_breakout_floor + 2:
            setup = "Session range"
    elif trading_style == "intraday" and breakout_score < 58:
        setup = "Session range"

    if isinstance(price_change_percent, (int, float)):
        if price_change_percent <= -1.0 and signal == "Ready":
            signal = "Watch"
            bias = "Watch for reclaim"
        elif price_change_percent <= -1.8:
            signal = "Cool-off"
            bias = "Wait"
            if setup == "Fast momentum":
                setup = "Range / reset"

    return bias, setup, signal


def _build_market_checklist(market_type: str, trading_style: str, is_live: bool) -> list[str]:
    if market_type == "futures" and trading_style == "scalping":
        return [
            "Trade only confirmed breaks and avoid late entries.",
            "Reduce size fast when volatility expands or the trigger weakens.",
            "Keep focus on the cleanest one or two names, not the whole tape.",
        ]
    if market_type == "futures":
        return [
            "Prefer continuation structure over raw velocity before taking risk.",
            "Wait for alignment between pulse and breakout before sizing normally.",
            "Reduce size when volatility is explosive and the breakout score is below 60.",
        ]
    if trading_style == "scalping":
        return [
            "Prioritize coins with pulse score above 70 before taking aggressive entries.",
            "Trade only confirmed breaks and avoid late entries.",
            "Use the live badge as confirmation, not as a replacement for trade risk management."
            if is_live
            else "Wait for alignment between pulse and breakout before chasing late moves.",
        ]
    return [
        "Prioritize assets with positive 24h change and breakout score above 65."
        if is_live
        else "Prioritize coins with pulse score above 70 before taking aggressive entries.",
        "Reduce size when volatility expands but price closes far from the 24h high."
        if is_live
        else "Reduce size when volatility is explosive and the breakout score is below 60.",
        "Use the live badge as confirmation, not as a replacement for trade risk management."
        if is_live
        else "Wait for alignment between pulse and breakout before chasing late moves.",
    ]


def _format_utc_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _format_signal_price(value: float | None) -> str | None:
    if not isinstance(value, (int, float)) or value <= 0:
        return None

    if value >= 1000:
        return f"${value:,.0f}"
    if value >= 1:
        return f"${value:,.2f}"
    return f"${value:,.6f}"


@dataclass(frozen=True)
class SetupEvaluation:
    asset: dict[str, Any]
    market_type: str
    trading_style: str
    regime: str
    volatility_label: str
    strategy_profile: dict[str, float]
    archetype: str
    market_signal: str
    confidence: int
    trigger_quality: int
    setup_quality: int
    noise_score: int
    status: str
    environment_note: str | None = None


def _score_signal_confidence(asset: dict[str, Any]) -> int:
    structure_score = asset["pulse_score"] * 0.55 + asset["breakout_score"] * 0.45
    stability_score = max(30.0, 100.0 - abs(asset["volatility_score"] - 55) * 1.2)

    signal_bonus = {
        "Ready": 10,
        "Watch": 2,
        "Cool-off": -14,
    }.get(asset["signal"], 0)
    bias_bonus = {
        "Long bias": 6,
        "Watch for reclaim": 1,
        "Wait": -8,
    }.get(asset["bias"], 0)
    volatility_penalty = 8 if asset["volatility_score"] >= 82 and asset["signal"] != "Ready" else 0

    return _clamp_int(structure_score * 0.72 + stability_score * 0.28 + signal_bonus + bias_bonus - volatility_penalty)


def _score_trigger_quality(asset: dict[str, Any], market_type: str, trading_style: str) -> int:
    profile = _get_strategy_profile(market_type, trading_style)
    stability_score = max(35.0, 100.0 - abs(asset["volatility_score"] - 52) * 1.35)
    speed_penalty = 8 if trading_style == "scalping" and asset["volatility_score"] >= 80 else 0
    leverage_penalty = 5 if market_type == "futures" and asset["volatility_score"] >= 76 else 0
    signal_bonus = {
        "Ready": 12,
        "Watch": 4,
        "Cool-off": -10,
    }.get(asset["signal"], 0)
    setup_bonus = {
        "Trend continuation": 4,
        "Breakout watch": 2,
        "Fast momentum": 3 if market_type == "futures" and trading_style == "scalping" else -1,
        "Session range": -6,
        "Range / reset": -8,
    }.get(asset["setup"], 0)

    quality = (
        asset["breakout_score"] * 0.52
        + asset["pulse_score"] * 0.28
        + stability_score * 0.20
        + signal_bonus
        + setup_bonus
        - speed_penalty
        - leverage_penalty
        - profile["trigger_floor_adjustment"] * 0.8
    )
    return _clamp_int(quality)


def _score_setup_quality(
    asset: dict[str, Any],
    confidence: int,
    trigger_quality: int,
    regime: str,
    volatility_label: str,
    market_type: str,
    trading_style: str,
) -> int:
    profile = _get_strategy_profile(market_type, trading_style)
    alignment_score = max(28.0, 100.0 - abs(asset["pulse_score"] - asset["breakout_score"]) * 1.55)
    archetype_bonus = {
        "Trend continuation": 10,
        "Breakout watch": 4,
        "Range / reset": -8,
        "Session range": -3,
    }.get(asset["setup"], 0)
    if asset["setup"] == "Fast momentum":
        archetype_bonus = 8 if market_type == "futures" and volatility_label != "Explosive" and trigger_quality >= 74 else -2

    signal_bonus = {
        "Ready": 8,
        "Watch": 1,
        "Cool-off": -12,
    }.get(asset["signal"], 0)
    bias_bonus = {
        "Long bias": 5,
        "Watch for reclaim": 1,
        "Wait": -7,
    }.get(asset["bias"], 0)

    price_change = asset.get("price_change_percent")
    follow_through_bonus = 0.0
    if isinstance(price_change, (int, float)):
        if price_change >= 1.2:
            follow_through_bonus = 4.0
        elif price_change <= -1.0:
            follow_through_bonus = -6.0
        elif price_change < 0:
            follow_through_bonus = -3.0

    regime_adjustment = 0.0
    if regime == "Defensive chop":
        regime_adjustment = 4.0 if asset["signal"] == "Ready" and trigger_quality >= 76 else -5.0
    elif regime.startswith("Risk-on"):
        regime_adjustment = 3.0 if asset["signal"] == "Ready" else 0.0

    style_penalty = 6.0 if trading_style == "scalping" and asset["volatility_score"] >= 83 else 0.0
    market_bonus = 3.0 if market_type == "spot" and asset["setup"] == "Trend continuation" else 0.0
    market_penalty = 4.0 if market_type == "futures" and asset["setup"] in {"Range / reset", "Session range"} else 0.0
    score = (
        confidence * 0.34
        + trigger_quality * 0.32
        + alignment_score * 0.18
        + asset["pulse_score"] * 0.08
        + asset["breakout_score"] * 0.08
        + archetype_bonus
        + signal_bonus
        + bias_bonus
        + follow_through_bonus
        + regime_adjustment
        + market_bonus
        - market_penalty
        - style_penalty
        - profile["quality_floor_adjustment"] * 0.5
    )
    return _clamp_int(score)


def _score_setup_noise(
    asset: dict[str, Any],
    setup_quality: int,
    trigger_quality: int,
    regime: str,
    volatility_label: str,
    market_type: str,
    trading_style: str,
) -> int:
    profile = _get_strategy_profile(market_type, trading_style)
    metric_gap = abs(asset["pulse_score"] - asset["breakout_score"])
    volatility_noise = max(0.0, asset["volatility_score"] - 58) * 0.72
    setup_noise = {
        "Trend continuation": 0.0,
        "Breakout watch": 5.0,
        "Range / reset": 14.0,
        "Session range": 10.0,
    }.get(asset["setup"], 6.0)
    if asset["setup"] == "Fast momentum":
        setup_noise = 13.0 if volatility_label == "Explosive" else 8.0
        if market_type == "futures" and trading_style == "scalping" and trigger_quality >= 74:
            setup_noise -= 2.0

    signal_noise = {
        "Ready": 0.0,
        "Watch": 6.0,
        "Cool-off": 14.0,
    }.get(asset["signal"], 8.0)
    bias_noise = {
        "Long bias": 0.0,
        "Watch for reclaim": 4.0,
        "Wait": 10.0,
    }.get(asset["bias"], 6.0)

    price_change = asset.get("price_change_percent")
    follow_through_noise = 0.0
    if isinstance(price_change, (int, float)):
        if price_change <= -1.2:
            follow_through_noise = 8.0
        elif price_change < 0:
            follow_through_noise = 4.0

    regime_noise = 0.0
    if regime == "Defensive chop" and setup_quality < 80:
        regime_noise = 6.0
    elif regime == "Selective continuation" and setup_quality < 66:
        regime_noise = 3.0
    if market_type == "futures":
        regime_noise += 2.0
    if trading_style == "scalping":
        regime_noise += 2.0

    quality_relief = max(0.0, (setup_quality - 72) * 0.20)
    trigger_relief = max(0.0, (trigger_quality - 70) * 0.22)
    score = (
        18.0
        + metric_gap * 0.90
        + volatility_noise
        + setup_noise
        + signal_noise
        + bias_noise
        + follow_through_noise
        + regime_noise
        - profile["noise_cap_adjustment"] * 0.35
        - quality_relief
        - trigger_relief
    )
    return _clamp_int(score)


def _evaluate_setup_opportunity(
    asset: dict[str, Any],
    market_type: str,
    trading_style: str,
    regime: str,
    volatility_label: str,
) -> SetupEvaluation:
    strategy_profile = _get_strategy_profile(market_type, trading_style)
    confidence = _score_signal_confidence(asset)
    trigger_quality = _score_trigger_quality(asset, market_type, trading_style)
    setup_quality = _score_setup_quality(
        asset,
        confidence,
        trigger_quality,
        regime,
        volatility_label,
        market_type,
        trading_style,
    )
    noise_score = _score_setup_noise(
        asset,
        setup_quality,
        trigger_quality,
        regime,
        volatility_label,
        market_type,
        trading_style,
    )
    status, environment_note = _apply_environment_signal_filter(
        asset["signal"],
        confidence,
        regime,
        volatility_label,
        trigger_quality,
        setup_quality,
        noise_score,
        market_type,
        trading_style,
    )

    return SetupEvaluation(
        asset=asset,
        market_type=market_type,
        trading_style=trading_style,
        regime=regime,
        volatility_label=volatility_label,
        strategy_profile=strategy_profile,
        archetype=asset["setup"],
        market_signal=asset["signal"],
        confidence=confidence,
        trigger_quality=trigger_quality,
        setup_quality=setup_quality,
        noise_score=noise_score,
        status=status,
        environment_note=environment_note,
    )


def _evaluate_market_setups(market_overview: dict[str, Any]) -> list[SetupEvaluation]:
    market_type = market_overview["market_type"]
    trading_style = market_overview["trading_style"]
    regime = market_overview["regime"]
    volatility_label = market_overview["volatility_label"]
    return [
        _evaluate_setup_opportunity(asset, market_type, trading_style, regime, volatility_label)
        for asset in market_overview["assets"]
    ]


def _signal_conviction_label(confidence: int) -> str:
    if confidence >= 76:
        return "High conviction"
    if confidence >= 63:
        return "Building conviction"
    return "Low conviction"


def _signal_size_plan(
    status: str,
    volatility_score: int,
    setup_quality: int,
    noise_score: int,
    market_type: str,
    trading_style: str,
) -> str:
    profile = _get_strategy_profile(market_type, trading_style)
    if status == "Stand aside":
        return "No size. Keep it on alerts only until structure improves."
    if noise_score >= 60 + profile["noise_cap_adjustment"] or volatility_score >= (80 if market_type == "futures" else 82):
        return "Start with reduced size and add only after a clean confirmation."
    if status == "Active" and setup_quality >= 78 + profile["quality_floor_adjustment"] and noise_score <= 40 + profile["noise_cap_adjustment"]:
        return "Start normal size only after confirmation. Add only if follow-through holds."
    return "Use starter size only if the trigger confirms. Avoid full size on anticipation."


def _signal_entry_trigger(status: str, last_price: float | None, trading_style: str) -> str:
    if not isinstance(last_price, (int, float)) or last_price <= 0:
        if status == "Active":
            return "Enter only after the next confirmation candle holds."
        if status == "Watch":
            return "Wait for a reclaim trigger before opening risk."
        return "No trigger yet. Leave it on standby."

    trigger_buffer = 0.0025 if trading_style == "scalping" else 0.006
    reclaim_price = _format_signal_price(last_price * (1 + trigger_buffer))
    hold_price = _format_signal_price(last_price * (1 - trigger_buffer))

    if status == "Active":
        return f"Act only if price holds above {hold_price} after confirmation."
    if status == "Watch":
        return f"Trigger only on a reclaim through {reclaim_price} with follow-through."
    return f"Stand aside until price reclaims {reclaim_price}."


def _signal_sort_key(setup: dict[str, Any]) -> tuple[int, int, int, int]:
    status_priority = {
        "Active": 0,
        "Watch": 1,
        "Stand aside": 2,
    }.get(setup["status"], 3)
    return (
        status_priority,
        -setup.get("setup_quality", setup["confidence"]),
        setup.get("noise_score", 99),
        -setup.get("trigger_quality", 0),
    )


def _apply_environment_signal_filter(
    market_signal: str,
    confidence: int,
    regime: str,
    volatility_label: str,
    trigger_quality: int,
    setup_quality: int,
    noise_score: int,
    market_type: str,
    trading_style: str,
) -> tuple[str, str | None]:
    profile = _get_strategy_profile(market_type, trading_style)
    trigger_floor = profile["trigger_floor_adjustment"]
    quality_floor = profile["quality_floor_adjustment"]
    noise_cap = profile["noise_cap_adjustment"]
    if market_signal == "Cool-off":
        return ("Stand aside", None)

    if setup_quality < 56 + quality_floor and noise_score >= 60 + noise_cap:
        return ("Stand aside", "Downgraded because volatility is too unstable for a reclaim setup right now.")

    if regime == "Defensive chop":
        if market_signal == "Ready" and (
            confidence < 80 + quality_floor
            or trigger_quality < 76 + trigger_floor
            or setup_quality < 76 + quality_floor
            or noise_score > 42 + noise_cap
        ):
            return ("Watch", "Downgraded because the broader tape is defensive. Wait for stronger confirmation.")
        if market_signal == "Watch" and (
            confidence < 72 + quality_floor
            or trigger_quality < 68 + trigger_floor
            or setup_quality < 68 + quality_floor
            or noise_score > 48 + noise_cap
        ):
            return ("Stand aside", "Downgraded because the broader tape is defensive and the reclaim is still weak.")
    elif regime == "Selective continuation":
        if market_signal == "Ready" and (
            trigger_quality < 68 + trigger_floor
            or setup_quality < 66 + quality_floor
            or noise_score > 54 + noise_cap
        ):
            return ("Watch", None)
        if market_signal == "Watch" and (
            confidence < 70 + quality_floor
            or trigger_quality < 61 + trigger_floor
            or setup_quality < 60 + quality_floor
        ) and noise_score > 52 + noise_cap:
            return ("Stand aside", None)
    elif regime.startswith("Risk-on"):
        if (
            market_signal == "Ready"
            and trigger_quality >= 78 + trigger_floor
            and setup_quality >= 78 + quality_floor
            and noise_score <= 36 + noise_cap
        ):
            return ("Active", None)

    if volatility_label == "Explosive":
        if market_signal == "Ready" and (
            confidence < 76 + quality_floor
            or trigger_quality < 72 + trigger_floor
            or setup_quality < 70 + quality_floor
            or noise_score > 48 + noise_cap
        ):
            return ("Watch", "Downgraded because volatility is still too fast for a clean first entry.")
        if market_signal == "Watch" and (
            confidence < 68 + quality_floor
            or trigger_quality < 65 + trigger_floor
            or setup_quality < 62 + quality_floor
            or noise_score > 56 + noise_cap
        ):
            return ("Stand aside", "Downgraded because volatility is too unstable for a reclaim setup right now.")

    if market_signal == "Ready":
        return ("Active", None)
    if market_signal == "Watch":
        return ("Watch", None)
    return ("Stand aside", None)


def _signal_invalidation(status: str, last_price: float | None, trading_style: str) -> str:
    if not isinstance(last_price, (int, float)) or last_price <= 0:
        return "Invalidation depends on structure. Re-check the chart before taking risk."

    buffer_pct = 0.0035 if trading_style == "scalping" else 0.008
    if status == "Active":
        level = _format_signal_price(last_price * (1 - buffer_pct))
        return f"Abort if price loses {level} after the confirmation instead of holding above it."
    if status == "Watch":
        level = _format_signal_price(last_price * (1 - buffer_pct * 0.75))
        return f"Stay flat if price keeps closing below {level} and the reclaim never sticks."

    level = _format_signal_price(last_price * (1 - buffer_pct * 1.4))
    return f"Skip it until structure repairs above {level} with momentum."


def _market_style_context_note(market_type: str, trading_style: str, regime: str, volatility_label: str) -> str:
    if market_type == "futures" and trading_style == "scalping":
        if volatility_label == "Explosive":
            return "Futures scalping in explosive conditions. Demand cleaner confirmation and smaller size."
        return "Futures scalping context. Speed matters, but only with a clean trigger."
    if market_type == "futures":
        return "Futures context. Keep leverage selective and avoid weak continuation."
    if trading_style == "scalping":
        return "Spot scalping context. Timing matters more than broad patience here."
    if regime == "Defensive chop":
        return "Spot intraday in defensive tape. Patience matters more than forcing entries."
    return "Spot intraday context. Let structure confirm before committing size."


def _confidence_explanation(
    confidence: int,
    trigger_quality: int,
    setup_quality: int,
    noise_score: int,
) -> str:
    if confidence >= 80 and trigger_quality >= 76 and setup_quality >= 76 and noise_score <= 42:
        return "Confidence is strong because structure, trigger, and noise are aligned."
    if confidence >= 70 and trigger_quality >= 68 and setup_quality >= 66 and noise_score <= 52:
        return "Confidence is constructive, but confirmation still matters."
    if noise_score >= 58:
        return "Confidence is capped by noise. Wait for cleaner structure."
    return "Confidence is still building. Keep risk small until confirmation improves."


def _signal_why_this_signal(evaluation: SetupEvaluation) -> str:
    if evaluation.status == "Active":
        return f"{evaluation.archetype} is leading with a cleaner trigger than the rest."
    if evaluation.status == "Watch":
        return f"{evaluation.archetype} is constructive, but still needs confirmation."
    return f"{evaluation.archetype} is visible, but the edge is not clean enough yet."


def _build_signal_setup_from_evaluation(
    evaluation: SetupEvaluation,
    timeframe: str,
    level: str | None = None,
) -> dict[str, Any]:
    asset = evaluation.asset
    volatility_score = asset["volatility_score"]
    conviction = _signal_conviction_label(evaluation.confidence)
    level_profile = _get_signal_level_profile(level)

    high_noise_floor = 60 if evaluation.market_type == "futures" and evaluation.trading_style == "scalping" else 62
    medium_noise_floor = 44 if evaluation.market_type == "futures" and evaluation.trading_style == "scalping" else 46
    high_volatility_floor = 76 if evaluation.market_type == "futures" and evaluation.trading_style == "scalping" else 78
    medium_volatility_floor = 56 if evaluation.market_type == "futures" and evaluation.trading_style == "scalping" else 58

    if evaluation.noise_score >= high_noise_floor or volatility_score >= high_volatility_floor:
        risk_note = "High velocity. Cut size and avoid chasing extension candles."
    elif evaluation.noise_score >= medium_noise_floor or volatility_score >= medium_volatility_floor:
        risk_note = "Moderate volatility. Wait for confirmation before committing full size."
    else:
        risk_note = "Controlled conditions. Favor clean structure over speed."

    if evaluation.status == "Active":
        direction = "Long continuation" if asset["bias"] == "Long bias" else "Momentum reclaim"
        entry_plan = f"{evaluation.archetype} setup. Enter only if strength holds after the next confirmation."
    elif evaluation.status == "Watch":
        direction = "Reclaim watch"
        entry_plan = f"{evaluation.archetype} setup. Wait for confirmation before opening risk."
    else:
        direction = "No edge yet"
        entry_plan = "No clean trigger yet. Protect capital and wait for structure to improve."

    if evaluation.environment_note:
        risk_note = f"{risk_note} {evaluation.environment_note}"

    if level_profile["label"] == "beginner":
        if evaluation.status == "Active":
            entry_plan = "One clean setup. Wait for confirmation, then act."
        elif evaluation.status == "Watch":
            entry_plan = "Watch this setup and wait for a clean reclaim."
        else:
            entry_plan = "No action now. Stay patient."
        risk_note = "Use one clear action, not constant monitoring."
    elif level_profile["label"] == "medium":
        if evaluation.status == "Active":
            entry_plan = f"{evaluation.archetype} setup. Use the trigger, size plan, and invalidation together."
        elif evaluation.status == "Watch":
            entry_plan = f"{evaluation.archetype} setup. Wait for reclaim confirmation before opening risk."
        else:
            entry_plan = "Keep it on watch only until structure and momentum improve together."

    return {
        "symbol": asset["symbol"],
        "status": evaluation.status,
        "direction": direction,
        "confidence": evaluation.confidence,
        "trigger_quality": evaluation.trigger_quality,
        "setup_quality": evaluation.setup_quality,
        "noise_score": evaluation.noise_score,
        "conviction": conviction,
        "confidence_explanation": _confidence_explanation(
            evaluation.confidence,
            evaluation.trigger_quality,
            evaluation.setup_quality,
            evaluation.noise_score,
        ),
        "timeframe": timeframe if level_profile["label"] == "pro" else ("Execution window" if level_profile["label"] == "medium" else "Focus window"),
        "entry_plan": entry_plan,
        "why_this_signal": _signal_why_this_signal(evaluation),
        "context_note": _market_style_context_note(
            evaluation.market_type,
            evaluation.trading_style,
            evaluation.regime,
            evaluation.volatility_label,
        ),
        "entry_trigger": _signal_entry_trigger(evaluation.status, asset.get("last_price"), evaluation.trading_style),
        "invalidation": _signal_invalidation(evaluation.status, asset.get("last_price"), evaluation.trading_style),
        "size_plan": _signal_size_plan(
            evaluation.status,
            volatility_score,
            evaluation.setup_quality,
            evaluation.noise_score,
            evaluation.market_type,
            evaluation.trading_style,
        ),
        "risk_note": risk_note,
        "last_price": asset.get("last_price"),
        "price_change_percent": asset.get("price_change_percent"),
    }


def _round_alert_price(value: float | None) -> float | None:
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    return round(float(value), 6)


def _priority_rank(priority: str) -> int:
    return {
        "Low": 0,
        "Medium": 1,
        "High": 2,
    }.get(priority, 0)


def _priority_label(rank: int) -> str:
    return {
        0: "Low",
        1: "Medium",
        2: "High",
    }.get(max(0, min(2, rank)), "Low")


def _build_alert_item(
    setup: dict[str, Any],
    market_type: str,
    trading_style: str,
    regime: str,
    evaluation: SetupEvaluation | None = None,
) -> dict[str, Any]:
    profile = evaluation.strategy_profile if evaluation else _get_strategy_profile(market_type, trading_style)
    last_price = setup.get("last_price")
    price_change_percent = setup.get("price_change_percent")
    buffer_pct = 0.0035 if trading_style == "scalping" else 0.008
    confidence = evaluation.confidence if evaluation else setup.get("confidence", 60)
    trigger_quality = evaluation.trigger_quality if evaluation else setup.get("trigger_quality", setup.get("confidence", 60))
    setup_quality = evaluation.setup_quality if evaluation else setup.get("setup_quality", setup.get("confidence", 60))
    noise_score = evaluation.noise_score if evaluation else setup.get("noise_score", 50)
    signal_status = evaluation.status if evaluation else setup["status"]
    buffer_multiplier = 1.0 + max(0.0, noise_score - 42) / 180.0
    if market_type == "futures" and trading_style == "scalping":
        buffer_multiplier += 0.08
    if noise_score >= 58:
        buffer_multiplier += 0.06

    if signal_status == "Active":
        alert_type = "Continuation confirm"
        direction = "Bullish confirmation"
        if (
            trigger_quality >= profile["high_alert_trigger_floor"]
            and setup_quality >= profile["high_alert_quality_floor"]
            and noise_score <= profile["high_alert_noise_cap"]
        ):
            priority = "High"
        elif (
            trigger_quality >= profile["medium_alert_trigger_floor"]
            and setup_quality >= profile["medium_alert_quality_floor"]
            and noise_score <= profile["medium_alert_noise_cap"] + 4
        ):
            priority = "Medium"
        else:
            priority = "Low"
        trigger_price = last_price * (1 + buffer_pct * buffer_multiplier) if isinstance(last_price, (int, float)) else None
        thesis = (
            "Price is close to a valid continuation trigger. Stay ready for confirmation."
            if priority == "High"
            else "Structure is active, but trigger quality still needs a cleaner confirmation."
        )
        action_note = "Alert on breakout confirmation, then execute only if follow-through holds."
    elif signal_status == "Watch":
        alert_type = "Reclaim trigger"
        direction = "Reclaim watch"
        priority = (
            "Medium"
            if (
                trigger_quality >= profile["medium_alert_trigger_floor"]
                and setup_quality >= profile["medium_alert_quality_floor"]
                and noise_score <= profile["medium_alert_noise_cap"]
            )
            else "Low"
        )
        trigger_price = (
            last_price * (1 + buffer_pct * 1.15 * buffer_multiplier)
            if isinstance(last_price, (int, float))
            else None
        )
        thesis = "Structure is improving, but it still needs a reclaim before risk makes sense."
        action_note = "Let the alert bring the pair back to you instead of front-running the move."
    else:
        alert_type = "Recovery trigger"
        direction = "Standby recovery"
        priority = "Low"
        trigger_price = (
            last_price * (1 + buffer_pct * 1.8 * buffer_multiplier)
            if isinstance(last_price, (int, float))
            else None
        )
        thesis = "No clean edge yet. Only a stronger recovery should bring this back into focus."
        action_note = "Keep it on alerts only and skip active risk until the structure resets."

    if regime == "Defensive chop" and priority == "Medium" and noise_score >= 48 + profile["noise_cap_adjustment"]:
        priority = "Low"

    distance_percent = None
    if isinstance(last_price, (int, float)) and last_price > 0 and isinstance(trigger_price, (int, float)):
        distance_percent = round(((trigger_price - last_price) / last_price) * 100.0, 2)

    priority_rank = _priority_rank(priority)
    near_trigger_floor = 0.45 if trading_style == "scalping" else 0.9
    very_noisy = noise_score >= 58 or confidence < 62
    clean_setup = (
        trigger_quality >= profile["medium_alert_trigger_floor"] + 4
        and setup_quality >= profile["medium_alert_quality_floor"] + 4
        and noise_score <= profile["medium_alert_noise_cap"] - 4
    )

    if market_type == "futures" and trading_style == "scalping" and priority_rank >= 1:
        if trigger_quality < profile["high_alert_trigger_floor"] + 2 or setup_quality < profile["high_alert_quality_floor"] + 2:
            priority_rank -= 1

    if very_noisy and priority_rank >= 1:
        priority_rank -= 1
    elif clean_setup and isinstance(distance_percent, (int, float)) and distance_percent <= near_trigger_floor and priority_rank < 2:
        priority_rank += 1

    if regime == "Defensive chop" and priority_rank == 1 and noise_score >= 48 + profile["noise_cap_adjustment"]:
        priority_rank = 0

    priority = _priority_label(priority_rank)

    return {
        "symbol": setup["symbol"],
        "alert_type": alert_type,
        "direction": direction,
        "priority": priority,
        "trigger_price": _round_alert_price(trigger_price),
        "distance_percent": distance_percent,
        "thesis": thesis,
        "why_this_signal": setup.get("why_this_signal", thesis),
        "confidence_explanation": _confidence_explanation(
            confidence,
            trigger_quality,
            setup_quality,
            noise_score,
        ),
        "context_note": _market_style_context_note(
            market_type,
            trading_style,
            regime,
            "Explosive" if noise_score >= 60 else ("Active" if noise_score >= 46 else "Compressed"),
        ),
        "action_note": action_note,
        "invalidation": setup.get("invalidation", "Invalidation depends on structure. Re-check before reacting."),
        "risk_note": setup.get("risk_note", "Wait for cleaner confirmation before reacting aggressively."),
        "last_price": last_price,
        "price_change_percent": price_change_percent,
    }


def _scanner_status_rank(status: str) -> int:
    return {
        "Hot": 0,
        "Building": 1,
        "Early": 2,
    }.get(status, 3)


def _scanner_urgency(distance_percent: float | None, evaluation: SetupEvaluation | None = None) -> str:
    if evaluation:
        if (
            isinstance(distance_percent, (int, float))
            and distance_percent <= (0.28 if evaluation.trading_style == "scalping" else 0.55)
            and evaluation.setup_quality >= 76
            and evaluation.noise_score <= 42
        ):
            return "Immediate"
        if (
            isinstance(distance_percent, (int, float))
            and distance_percent <= (0.75 if evaluation.trading_style == "scalping" else 1.5)
            and evaluation.setup_quality >= 68
            and evaluation.noise_score <= 52
        ):
            return "Near"
    if not isinstance(distance_percent, (int, float)):
        return "Monitor"
    if distance_percent <= 0.35:
        return "Immediate"
    if distance_percent <= 1.2:
        return "Near"
    return "Early"


def _scanner_status(
    signal_status: str,
    priority: str,
    distance_percent: float | None,
    trigger_quality: int,
    setup_quality: int,
    noise_score: int,
    market_type: str,
    trading_style: str,
    evaluation: SetupEvaluation | None = None,
) -> str:
    profile = evaluation.strategy_profile if evaluation else _get_strategy_profile(market_type, trading_style)
    if (
        priority == "High"
        and signal_status == "Active"
        and trigger_quality >= 76 + profile["trigger_floor_adjustment"]
        and setup_quality >= 72 + profile["quality_floor_adjustment"]
        and noise_score <= 42 + profile["noise_cap_adjustment"]
    ):
        return "Hot"
    if (
        priority in {"High", "Medium"}
        and setup_quality >= 62 + profile["quality_floor_adjustment"]
        and noise_score <= 56 + profile["noise_cap_adjustment"]
    ):
        return "Building"
    if (
        signal_status == "Watch"
        and trigger_quality >= 62 + profile["trigger_floor_adjustment"]
        and setup_quality >= 60 + profile["quality_floor_adjustment"]
        and noise_score <= 58 + profile["noise_cap_adjustment"]
    ):
        return "Building"
    if (
        isinstance(distance_percent, (int, float))
        and distance_percent <= 0.35
        and setup_quality >= 68 + profile["quality_floor_adjustment"]
        and noise_score <= 50 + profile["noise_cap_adjustment"]
    ):
        return "Hot"
    return "Early"


def _scanner_environment_adjustment(
    regime: str,
    setup: dict[str, Any],
    alert_item: dict[str, Any],
    market_type: str,
    trading_style: str,
    evaluation: SetupEvaluation | None = None,
) -> float:
    profile = evaluation.strategy_profile if evaluation else _get_strategy_profile(market_type, trading_style)
    distance_percent = alert_item.get("distance_percent")
    adjustment = 0.0
    setup_quality = evaluation.setup_quality if evaluation else setup.get("setup_quality", setup.get("confidence", 60))
    noise_score = evaluation.noise_score if evaluation else setup.get("noise_score", 50)
    signal_status = evaluation.status if evaluation else setup["status"]

    if regime == "Defensive chop":
        adjustment -= 8.0
        if signal_status == "Active" and setup_quality >= 82 and noise_score <= 40:
            adjustment += 4.0
        if isinstance(distance_percent, (int, float)) and distance_percent <= 0.6:
            adjustment += 2.0
    elif regime == "Selective continuation":
        adjustment += 2.0
    else:
        adjustment += 4.0

    if noise_score >= 60:
        adjustment -= 5.0
    elif noise_score <= 36:
        adjustment += 3.0

    if market_type == "futures":
        adjustment -= 2.0 if noise_score >= 48 else 1.0
    if trading_style == "scalping" and isinstance(distance_percent, (int, float)):
        adjustment += max(0.0, (1.1 - min(distance_percent, 1.1))) * 4.0 * profile["distance_weight"]

    return adjustment


def _scanner_score(
    asset: dict[str, Any],
    setup: dict[str, Any],
    alert_item: dict[str, Any],
    regime: str,
    market_type: str,
    trading_style: str,
    watchlist_match: bool = False,
    evaluation: SetupEvaluation | None = None,
) -> int:
    profile = evaluation.strategy_profile if evaluation else _get_strategy_profile(market_type, trading_style)
    priority_bonus = {
        "High": 12,
        "Medium": 6,
        "Low": 0,
    }.get(alert_item["priority"], 0)
    distance_bonus = 0.0
    distance_percent = alert_item.get("distance_percent")
    if isinstance(distance_percent, (int, float)):
        distance_bonus = max(0.0, 12.0 - min(distance_percent, 6.0) * 2.0) * profile["distance_weight"]

    confidence = evaluation.confidence if evaluation else setup["confidence"]
    trigger_quality = evaluation.trigger_quality if evaluation else setup.get("trigger_quality", setup["confidence"])
    setup_quality = evaluation.setup_quality if evaluation else setup.get("setup_quality", setup["confidence"])
    noise_score = evaluation.noise_score if evaluation else setup.get("noise_score", 50)
    status = evaluation.status if evaluation else setup["status"]

    cleanliness_bonus = 0.0
    if setup_quality >= 78 and noise_score <= 40:
        cleanliness_bonus += 6.0
    elif setup_quality >= 70 and noise_score <= 48:
        cleanliness_bonus += 3.0

    if noise_score >= 60:
        cleanliness_bonus -= 8.0
    elif noise_score >= 52:
        cleanliness_bonus -= 4.0

    if (
        isinstance(distance_percent, (int, float))
        and distance_percent <= (0.4 if trading_style == "scalping" else 0.85)
        and setup_quality >= 72
        and noise_score <= 46
    ):
        cleanliness_bonus += 5.0

    if market_type == "futures" and trading_style == "scalping":
        if trigger_quality < 72 or setup_quality < 68 or noise_score > 50:
            cleanliness_bonus -= 5.0
        if status != "Active" and noise_score >= 52:
            cleanliness_bonus -= 3.0

    base_score = (
        asset["pulse_score"] * (0.16 if trading_style == "scalping" else 0.22)
        + asset["breakout_score"] * (0.24 if trading_style == "scalping" else 0.18)
        + confidence * 0.18
        + trigger_quality * 0.16
        + setup_quality * 0.18
        + distance_bonus
        + priority_bonus
        + cleanliness_bonus
        + _scanner_environment_adjustment(regime, setup, alert_item, market_type, trading_style, evaluation)
        - noise_score * 0.14
        + (profile["watchlist_bonus"] if watchlist_match else 0)
    )
    return _clamp_int(base_score, minimum=1, maximum=99)


def _scanner_invalidation(
    status: str,
    last_price: float | None,
    trigger_price: float | None,
    trading_style: str,
) -> str:
    if not isinstance(last_price, (int, float)) or last_price <= 0:
        return "Invalidation depends on structure. Review the chart before acting."

    buffer_pct = 0.004 if trading_style == "scalping" else 0.009
    if status == "Hot" and isinstance(trigger_price, (int, float)):
        level = _format_signal_price(trigger_price * (1 - buffer_pct))
        return f"Abort if price loses {level} after the trigger instead of holding above it."

    level = _format_signal_price(last_price * (1 - buffer_pct * 1.6))
    return f"Stand down if price slips back under {level} and momentum fades."


def _scanner_trigger_plan(alert_item: dict[str, Any], setup: dict[str, Any]) -> str:
    trigger_price = _format_signal_price(alert_item.get("trigger_price"))
    if trigger_price:
        return f"{alert_item['alert_type']} around {trigger_price}. {setup['entry_trigger']}"
    return setup["entry_trigger"]


def _should_include_scanner_candidate(
    setup: dict[str, Any],
    alert_item: dict[str, Any],
    scanner_score: int,
    watchlist_match: bool,
    market_type: str,
    trading_style: str,
    evaluation: SetupEvaluation | None = None,
) -> bool:
    profile = evaluation.strategy_profile if evaluation else _get_strategy_profile(market_type, trading_style)
    if watchlist_match:
        return True
    signal_status = evaluation.status if evaluation else setup["status"]
    if signal_status != "Stand aside":
        return True
    if alert_item["priority"] != "Low":
        return True

    setup_quality = evaluation.setup_quality if evaluation else setup.get("setup_quality", setup.get("confidence", 60))
    noise_score = evaluation.noise_score if evaluation else setup.get("noise_score", 50)
    trigger_quality = evaluation.trigger_quality if evaluation else setup.get("trigger_quality", setup.get("confidence", 60))
    if (
        market_type == "futures"
        and trading_style == "scalping"
        and noise_score >= 54
        and setup_quality < 68
        and trigger_quality < 70
    ):
        return False
    if noise_score >= 60 and setup_quality < 66:
        return False
    return (
        scanner_score >= profile["scanner_filter_floor"]
        or (
            setup_quality >= 62 + profile["quality_floor_adjustment"]
            and noise_score <= 52 + profile["noise_cap_adjustment"]
        )
    )


def _scanner_sort_key(candidate: dict[str, Any]) -> tuple[int, int, int]:
    return (
        _scanner_status_rank(candidate["status"]),
        -candidate["scanner_score"],
        candidate["rank"],
    )


def _alert_priority_sort_key(item: dict[str, Any]) -> tuple[int, float]:
    priority_order = {
        "High": 0,
        "Medium": 1,
        "Low": 2,
    }.get(item["priority"], 3)
    distance = item["distance_percent"] if isinstance(item.get("distance_percent"), (int, float)) else 999.0
    return (priority_order, distance)


def _priority_meets_minimum(priority: str, minimum: str) -> bool:
    ranks = {
        "high": 3,
        "medium": 2,
        "low": 1,
        "High": 3,
        "Medium": 2,
        "Low": 1,
    }
    return ranks.get(priority, 0) >= ranks.get(minimum, 0)


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _build_alert_digest_key(alerts_overview: dict[str, Any], filtered_items: list[dict[str, Any]]) -> str:
    digest_payload = {
        "headline": alerts_overview["headline"],
        "next_action": alerts_overview["next_action"],
        "top_symbol": alerts_overview.get("top_symbol"),
        "data_mode": alerts_overview.get("data_mode"),
        "data_provider": alerts_overview.get("data_provider"),
        "items": [
            {
                "symbol": item["symbol"],
                "priority": item["priority"],
                "trigger_price": item.get("trigger_price"),
                "distance_percent": item.get("distance_percent"),
            }
            for item in filtered_items
        ],
    }
    return hashlib.sha256(json.dumps(digest_payload, sort_keys=True).encode()).hexdigest()


def _get_delivery_status(
    alerts_enabled: bool,
    last_sent_at: datetime | None,
    now: datetime,
) -> tuple[str, str | None, int]:
    if not alerts_enabled:
        return ("off", None, 0)

    if not last_sent_at or ALERT_MIN_INTERVAL_SECONDS <= 0:
        return ("armed", None, 0)

    next_eligible_at = last_sent_at + timedelta(seconds=ALERT_MIN_INTERVAL_SECONDS)
    remaining_seconds = max(0, int((next_eligible_at - now).total_seconds()))
    if remaining_seconds > 0:
        return ("cooldown", _format_utc_timestamp(next_eligible_at.timestamp()), remaining_seconds)

    return ("armed", None, 0)


def _is_urgent_alert_batch(filtered_items: list[dict[str, Any]]) -> bool:
    if not filtered_items:
        return False

    top_item = filtered_items[0]
    if top_item.get("priority") != "High":
        return False

    distance_percent = top_item.get("distance_percent")
    if not isinstance(distance_percent, (int, float)):
        return False

    return distance_percent <= 0.35


def _fetch_live_rows(coins: list[str]) -> tuple[dict[str, dict[str, float]], str, float, bool, bool]:
    normalized_coins = tuple(_normalize_coin_list(coins))
    cache_key = (MARKET_DATA_PROVIDER, normalized_coins)
    now = time.time()
    cached_entry = _LIVE_MARKET_CACHE.get(cache_key) if MARKET_DATA_CACHE_SECONDS > 0 else None

    if MARKET_DATA_CACHE_SECONDS > 0:
        if cached_entry and cached_entry["expires_at"] > now:
            return cached_entry["rows"], cached_entry["provider"], cached_entry["fetched_at"], True, False

    last_error: Exception | None = None
    live_rows: dict[str, dict[str, float]] = {}
    data_provider = MARKET_DATA_PROVIDER

    for provider in _get_live_provider_sequence():
        try:
            candidate_rows = _fetch_provider_rows(provider, list(normalized_coins))
        except Exception as error:
            last_error = error
            continue

        if len(candidate_rows) == len(normalized_coins):
            live_rows = candidate_rows
            data_provider = provider
            break

    if not live_rows:
        if cached_entry and cached_entry["rows"]:
            return cached_entry["rows"], cached_entry["provider"], cached_entry["fetched_at"], True, True
        if last_error is not None:
            raise last_error
        raise ValueError("No live provider returned a complete market snapshot.")

    if MARKET_DATA_CACHE_SECONDS > 0 and len(live_rows) == len(normalized_coins):
        _LIVE_MARKET_CACHE[cache_key] = {
            "rows": live_rows,
            "provider": data_provider,
            "fetched_at": now,
            "expires_at": now + MARKET_DATA_CACHE_SECONDS,
        }

    return live_rows, data_provider, now, False, False


def _build_modelled_market_overview(
    user_id: int,
    coins: list[str],
    market_type: str,
    trading_style: str,
) -> dict[str, Any]:
    sentiment_score = _stable_int(f"{user_id}:{market_type}:{trading_style}:sentiment", 52, 81)
    volatility_score = _stable_int(f"{user_id}:{market_type}:{trading_style}:volatility", 34, 88)

    if sentiment_score >= 72:
        regime = "Risk-on rotation"
    elif sentiment_score >= 60:
        regime = "Selective continuation"
    else:
        regime = "Defensive chop"

    if volatility_score >= 72:
        volatility_label = "Explosive"
    elif volatility_score >= 54:
        volatility_label = "Active"
    else:
        volatility_label = "Compressed"

    focus_window = "Fast reaction window" if trading_style == "scalping" else "Session continuation window"
    outlook_headline = (
        "Momentum is broadening across your watchlist."
        if sentiment_score >= 70
        else "Leadership is narrow, so coin selection matters more than direction."
    )

    checklist = _build_market_checklist(market_type, trading_style, is_live=False)

    assets: list[dict[str, Any]] = []
    for index, symbol in enumerate(coins):
        pulse_score = _stable_int(f"{user_id}:{symbol}:pulse", 48, 92)
        breakout_score = _stable_int(f"{user_id}:{symbol}:breakout", 40, 90)
        coin_volatility = _stable_int(f"{user_id}:{symbol}:volatility", 35, 94)

        bias, setup, signal = _classify_market_asset(
            pulse_score,
            breakout_score,
            coin_volatility,
            market_type,
            trading_style,
        )

        assets.append(
            {
                "symbol": symbol,
                "pulse_score": pulse_score,
                "breakout_score": breakout_score,
                "volatility_score": coin_volatility,
                "bias": bias,
                "setup": setup,
                "signal": signal,
                "last_price": None,
                "price_change_percent": None,
                "quote_volume": None,
            }
        )

    return {
        "market_type": market_type,
        "trading_style": trading_style,
        "regime": regime,
        "sentiment_score": sentiment_score,
        "volatility_label": volatility_label,
        "focus_window": focus_window,
        "outlook_headline": outlook_headline,
        "checklist": checklist,
        "assets": assets,
        "data_mode": "modelled",
        "data_provider": None,
        "data_updated_at": None,
        "data_cached": False,
        "data_stale": False,
    }


def _http_get_json(endpoint: str) -> Any:
    http_request = request.Request(
        endpoint,
        headers={
            "Accept": "application/json",
            "User-Agent": "ScannerHT/1.0",
        },
    )

    with request.urlopen(http_request, timeout=5) as response:
        return json.loads(response.read().decode())


def _fetch_binance_tickers(coins: list[str]) -> dict[str, dict[str, float]]:
    symbols = [_format_live_symbol(symbol) for symbol in coins]
    encoded_symbols = parse.quote(json.dumps(symbols, separators=(",", ":")))
    endpoint = f"https://api.binance.com/api/v3/ticker/24hr?symbols={encoded_symbols}&type=MINI"
    payload = _http_get_json(endpoint)
    if not isinstance(payload, list):
        return {}

    live_rows: dict[str, dict[str, float]] = {}
    for symbol in coins:
        ticker = next((item for item in payload if item.get("symbol") == _format_live_symbol(symbol)), None)
        if not ticker:
            continue

        last_price = _safe_float(ticker.get("lastPrice"))
        open_price = _safe_float(ticker.get("openPrice"))
        high_price = _safe_float(ticker.get("highPrice"))
        low_price = _safe_float(ticker.get("lowPrice"))
        quote_volume = _safe_float(ticker.get("quoteVolume"))
        change_pct = ((last_price - open_price) / open_price * 100.0) if open_price else 0.0

        live_rows[symbol] = {
            "last_price": last_price,
            "high_price": high_price,
            "low_price": low_price,
            "change_pct": change_pct,
            "quote_volume": quote_volume,
        }

    return live_rows


def _fetch_coingecko_markets(coins: list[str]) -> dict[str, dict[str, float]]:
    ids = [COINGECKO_ID_MAP.get(symbol) for symbol in coins if COINGECKO_ID_MAP.get(symbol)]
    endpoint = (
        "https://api.coingecko.com/api/v3/coins/markets"
        f"?vs_currency=usd&ids={','.join(ids)}&price_change_percentage=24h"
    )
    payload = _http_get_json(endpoint)
    if not isinstance(payload, list):
        return {}

    rows_by_id = {item.get("id"): item for item in payload if isinstance(item, dict)}
    live_rows: dict[str, dict[str, float]] = {}

    for symbol in coins:
        coin_id = COINGECKO_ID_MAP.get(symbol)
        row = rows_by_id.get(coin_id)
        if not row:
            continue

        live_rows[symbol] = {
            "last_price": _safe_float(row.get("current_price")),
            "high_price": _safe_float(row.get("high_24h")),
            "low_price": _safe_float(row.get("low_24h")),
            "change_pct": _safe_float(row.get("price_change_percentage_24h")),
            "quote_volume": _safe_float(row.get("total_volume")),
        }

    return live_rows


def _fetch_coinbase_markets(coins: list[str]) -> dict[str, dict[str, float]]:
    live_rows: dict[str, dict[str, float]] = {}

    for symbol in coins:
        product_id = COINBASE_PRODUCT_MAP.get(symbol)
        if not product_id:
            continue

        endpoint = f"https://api.exchange.coinbase.com/products/{product_id}/stats"
        payload = _http_get_json(endpoint)
        if not isinstance(payload, dict):
            continue

        last_price = _safe_float(payload.get("last"))
        open_price = _safe_float(payload.get("open"))
        high_price = _safe_float(payload.get("high"))
        low_price = _safe_float(payload.get("low"))
        base_volume = _safe_float(payload.get("volume"))
        quote_volume = base_volume * last_price
        change_pct = ((last_price - open_price) / open_price * 100.0) if open_price else 0.0

        live_rows[symbol] = {
            "last_price": last_price,
            "high_price": high_price,
            "low_price": low_price,
            "change_pct": change_pct,
            "quote_volume": quote_volume,
        }

    return live_rows


def _get_live_provider_sequence() -> list[str]:
    if MARKET_DATA_PROVIDER == "coinbase":
        return ["coinbase", "coingecko"]
    if MARKET_DATA_PROVIDER == "binance":
        return ["binance", "coingecko", "coinbase"]
    return ["coingecko", "coinbase"]


def _fetch_provider_rows(provider: str, coins: list[str]) -> dict[str, dict[str, float]]:
    if provider == "coinbase":
        return _fetch_coinbase_markets(coins)
    if provider == "coingecko":
        return _fetch_coingecko_markets(coins)
    return _fetch_binance_tickers(coins)


def _build_live_market_overview(
    coins: list[str],
    market_type: str,
    trading_style: str,
) -> dict[str, Any]:
    live_rows, data_provider, fetched_at, data_cached, data_stale = _fetch_live_rows(coins)

    assets: list[dict[str, Any]] = []
    change_values: list[float] = []
    range_values: list[float] = []

    for symbol in coins:
        row = live_rows.get(symbol)
        if not row:
            raise ValueError(f"Missing live market data for {symbol}.")

        last_price = row["last_price"]
        high_price = row["high_price"]
        low_price = row["low_price"]
        quote_volume = row["quote_volume"]
        change_pct = row["change_pct"]
        range_pct = ((high_price - low_price) / low_price * 100.0) if low_price else 0.0
        position_pct = (
            ((last_price - low_price) / (high_price - low_price) * 100.0)
            if high_price > low_price
            else 50.0
        )
        volume_score = min(20.0, max(0.0, math.log10(max(quote_volume, 1.0)) * 2.5))

        pulse_score = _clamp_int(50 + change_pct * 3 + (position_pct - 50) * 0.35 + volume_score)
        breakout_score = _clamp_int(45 + change_pct * 2 + position_pct * 0.35 + min(range_pct * 2, 18))
        coin_volatility = _clamp_int(range_pct * 5.5)

        bias, setup, signal = _classify_market_asset(
            pulse_score,
            breakout_score,
            coin_volatility,
            market_type,
            trading_style,
            change_pct,
        )

        assets.append(
            {
                "symbol": symbol,
                "pulse_score": pulse_score,
                "breakout_score": breakout_score,
                "volatility_score": coin_volatility,
                "bias": bias,
                "setup": setup,
                "signal": signal,
                "last_price": round(last_price, 6),
                "price_change_percent": round(change_pct, 2),
                "quote_volume": round(quote_volume, 2),
            }
        )
        change_values.append(change_pct)
        range_values.append(range_pct)

    avg_change = sum(change_values) / len(change_values) if change_values else 0.0
    avg_range = sum(range_values) / len(range_values) if range_values else 0.0
    avg_breakout = sum(asset["breakout_score"] for asset in assets) / len(assets) if assets else 50.0

    sentiment_score = _clamp_int(52 + avg_change * 6 + (avg_breakout - 50) * 0.35)

    if avg_change >= 2 and sentiment_score >= 68:
        regime = "Risk-on continuation"
    elif avg_change >= 0:
        regime = "Selective continuation"
    else:
        regime = "Defensive chop"

    if avg_range >= 5:
        volatility_label = "Explosive"
    elif avg_range >= 3:
        volatility_label = "Active"
    else:
        volatility_label = "Compressed"

    focus_window = "Fast reaction window" if trading_style == "scalping" else "Session continuation window"

    if avg_change >= 2:
        outlook_headline = "Live tape shows momentum leadership across your selected watchlist."
    elif avg_change >= 0:
        outlook_headline = "Live tape is mixed, so selection and timing matter more than broad direction."
    else:
        outlook_headline = "Live tape is defensive right now, so patience matters more than forcing entries."

    checklist = _build_market_checklist(market_type, trading_style, is_live=True)

    return {
        "market_type": market_type,
        "trading_style": trading_style,
        "regime": regime,
        "sentiment_score": sentiment_score,
        "volatility_label": volatility_label,
        "focus_window": focus_window,
        "outlook_headline": outlook_headline,
        "checklist": checklist,
        "assets": assets,
        "data_mode": f"live-{data_provider}",
        "data_provider": data_provider,
        "data_updated_at": _format_utc_timestamp(fetched_at),
        "data_cached": data_cached,
        "data_stale": data_stale,
    }


def _get_market_overview_raw(user_id: int, user: dict[str, Any] | None = None) -> dict[str, Any]:
    user = user or get_user(user_id)
    coins = _get_user_watchlist(user)
    market_type = user.get("market") or "spot"
    trading_style = user.get("trading_style") or "intraday"

    if MARKET_DATA_MODE == "live":
        try:
            return _build_live_market_overview(coins, market_type, trading_style)
        except Exception as error:
            print(f"Falling back to modelled market data: {error}")
            return _build_modelled_market_overview(user_id, coins, market_type, trading_style)

    return _build_modelled_market_overview(user_id, coins, market_type, trading_style)


def get_market_overview(user_id: int) -> dict[str, Any]:
    user = get_user(user_id)
    return _localize_payload(_get_market_overview_raw(user_id, user), user.get("language"))


def _build_signals_overview_from_market(
    market_overview: dict[str, Any],
    level: str | None = None,
    evaluations: list[SetupEvaluation] | None = None,
) -> dict[str, Any]:
    market_type = market_overview["market_type"]
    trading_style = market_overview["trading_style"]
    regime = market_overview["regime"]
    volatility_label = market_overview["volatility_label"]
    timeframe = "5m-15m execution" if trading_style == "scalping" else "1h-4h execution"
    level_profile = _get_signal_level_profile(level)
    evaluations = evaluations or _evaluate_market_setups(market_overview)

    setups: list[dict[str, Any]] = []
    ready_count = 0
    watch_count = 0
    cool_off_count = 0

    for evaluation in evaluations:
        if evaluation.status == "Active":
            ready_count += 1
        elif evaluation.status == "Watch":
            watch_count += 1
        else:
            cool_off_count += 1

        setups.append(_build_signal_setup_from_evaluation(evaluation, timeframe, level))

    setups.sort(key=_signal_sort_key)
    top_setup = setups[0] if setups else None

    if level_profile["label"] == "beginner" and top_setup:
        if top_setup["status"] == "Active":
            headline = "One clear setup is ready to watch closely."
            next_action = f"Focus on {top_setup['symbol']} only and wait for confirmation before acting."
        elif top_setup["status"] == "Watch":
            headline = "One setup deserves attention, but it still needs confirmation."
            next_action = f"Keep {top_setup['symbol']} in focus and wait for the trigger to confirm."
        else:
            headline = "No clean action is ready right now."
            next_action = "Stay patient and ignore weaker names until structure improves."
    elif level_profile["label"] == "medium" and ready_count >= 1 and top_setup:
        headline = "A guided setup stands out with a clear trigger and risk plan."
        next_action = f"Use {top_setup['symbol']} first, then check trigger, size, and invalidation before entry."
    elif level_profile["label"] == "medium" and watch_count >= 1 and top_setup:
        headline = "The watchlist is constructive, but confirmation still decides the trade."
        next_action = f"Keep {top_setup['symbol']} ready and wait for reclaim confirmation before taking risk."
    elif ready_count >= 2 and top_setup:
        headline = "Several setups are aligned. Focus on the cleanest continuation instead of forcing all of them."
        next_action = f"Prioritize {top_setup['symbol']} first and keep the others as secondary ideas."
    elif ready_count == 1 and top_setup:
        headline = "One setup stands out. Let the rest confirm before spreading attention too wide."
        next_action = f"Focus on {top_setup['symbol']} and act only if its trigger confirms cleanly."
    elif watch_count >= 2 and top_setup:
        headline = "Watchlist is forming, but confirmation still matters more than anticipation."
        next_action = f"Keep {top_setup['symbol']} at the top of the watchlist and wait for the reclaim trigger."
    else:
        headline = "No strong signal right now. Capital preservation is the active decision."
        next_action = "Stay selective. Keep alerts on and wait for structure plus momentum to improve."

    checklist = level_profile["checklist"]

    return {
        "market_type": market_overview["market_type"],
        "trading_style": trading_style,
        "regime": regime,
        "headline": headline,
        "execution_bias": f"{ready_count} active / {watch_count} watch / {cool_off_count} stand aside",
        "risk_posture": _score_risk_posture(volatility_label, market_type, trading_style),
        "next_action": next_action,
        "top_symbol": top_setup["symbol"] if top_setup else None,
        "checklist": checklist,
        "setups": setups,
        "ready_count": ready_count,
        "watch_count": watch_count,
        "cool_off_count": cool_off_count,
        "data_mode": market_overview["data_mode"],
        "data_provider": market_overview.get("data_provider"),
        "data_updated_at": market_overview.get("data_updated_at"),
        "data_cached": market_overview.get("data_cached", False),
        "data_stale": market_overview.get("data_stale", False),
    }


def _get_signals_overview_raw(user_id: int, user: dict[str, Any] | None = None) -> dict[str, Any]:
    user = user or get_user(user_id)
    market_overview = _get_market_overview_raw(user_id, user)
    signals_overview = _build_signals_overview_from_market(market_overview, user.get("level"))
    signal_limit = _get_effective_signal_limit(user)
    signals_overview["setups"] = signals_overview["setups"][:signal_limit]
    return signals_overview


def get_signals_overview(user_id: int) -> dict[str, Any]:
    user = get_user(user_id)
    localized = _localize_payload(_get_signals_overview_raw(user_id, user), user.get("language"))
    localized["execution_bias"] = _localize_execution_bias(localized["execution_bias"], user.get("language"))
    return localized


def _build_alerts_overview_from_signals(
    signals_overview: dict[str, Any],
    user: dict[str, Any],
    evaluations_by_symbol: dict[str, SetupEvaluation] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    last_sent_at = _parse_iso_timestamp(user.get("last_alert_sent_at"))
    delivery_status, next_eligible_at, cooldown_seconds = _get_delivery_status(
        bool(user.get("alerts_enabled")),
        last_sent_at,
        now,
    )
    trading_style = signals_overview["trading_style"]
    market_type = signals_overview["market_type"]
    minimum_priority = _get_effective_alerts_min_priority(user)
    items = [
        _build_alert_item(
            setup,
            market_type,
            trading_style,
            signals_overview["regime"],
            evaluation=evaluations_by_symbol.get(setup["symbol"]) if evaluations_by_symbol else None,
        )
        for setup in signals_overview["setups"]
    ]
    items.sort(key=_alert_priority_sort_key)
    visible_items = [item for item in items if _priority_meets_minimum(item["priority"], minimum_priority)]

    high_priority_count = sum(1 for item in visible_items if item["priority"] == "High")
    medium_priority_count = sum(1 for item in visible_items if item["priority"] == "Medium")
    low_priority_count = sum(1 for item in visible_items if item["priority"] == "Low")
    top_item = visible_items[0] if visible_items else None

    if high_priority_count >= 2 and top_item:
        headline = "Several alert candidates are close. Let alerts bring the market to you instead of camping on the chart."
        next_action = f"Arm the high-priority flow around {top_item['symbol']} first, then review the secondary names."
    elif high_priority_count == 1 and top_item:
        headline = "One alert stands out as the clearest near-term trigger."
        next_action = f"Keep {top_item['symbol']} on top of your alerts and only react if the trigger prints cleanly."
    elif medium_priority_count >= 1 and top_item:
        headline = "The watchlist is constructive, but most moves still need confirmation."
        next_action = f"Set reclaim alerts for {top_item['symbol']} and let the market come to your level."
    else:
        headline = "Nothing needs urgent attention right now. Alerts should protect focus, not create noise."
        next_action = "Stay selective. Keep only low-noise alerts active and wait for the structure to improve."

    active_window = "15m-1h follow-up" if trading_style == "scalping" else "1h-4h follow-up"
    minimum_priority_label = minimum_priority.capitalize()
    cooldown_minutes = max(1, math.ceil(cooldown_seconds / 60)) if cooldown_seconds else 0
    if delivery_status == "cooldown":
        delivery_note = (
            f"Telegram alert delivery is cooling down for {minimum_priority_label}+ ideas."
            f" Next window in about {cooldown_minutes} min."
        )
    elif user.get("alerts_enabled"):
        cadence_note = (
            f" Cooldown: about {max(1, ALERT_MIN_INTERVAL_SECONDS // 60)} min between repeated digests."
            if ALERT_MIN_INTERVAL_SECONDS
            else ""
        )
        delivery_note = (
            f"Telegram alert delivery is armed for {minimum_priority_label}+ ideas."
            f"{cadence_note}"
        )
    else:
        delivery_note = (
            f"Telegram delivery is off. Arm alerts to receive {minimum_priority_label}+ ideas without camping on charts."
        )

    return {
        "market_type": signals_overview["market_type"],
        "trading_style": trading_style,
        "regime": signals_overview["regime"],
        "headline": headline,
        "next_action": next_action,
        "active_window": active_window,
        "delivery_note": delivery_note,
        "delivery_status": delivery_status,
        "delivery_min_priority": minimum_priority_label,
        "delivery_last_sent_at": _format_utc_timestamp(last_sent_at.timestamp()) if last_sent_at else None,
        "delivery_next_eligible_at": next_eligible_at,
        "delivery_cooldown_seconds": cooldown_seconds,
        "top_symbol": top_item["symbol"] if top_item else signals_overview.get("top_symbol"),
        "items": visible_items,
        "high_priority_count": high_priority_count,
        "medium_priority_count": medium_priority_count,
        "low_priority_count": low_priority_count,
        "data_mode": signals_overview["data_mode"],
        "data_provider": signals_overview.get("data_provider"),
        "data_updated_at": signals_overview.get("data_updated_at"),
        "data_cached": signals_overview.get("data_cached", False),
        "data_stale": signals_overview.get("data_stale", False),
    }


def _get_alerts_overview_raw(user_id: int, user: dict[str, Any] | None = None) -> dict[str, Any]:
    user = user or get_user(user_id)
    market_overview = _get_market_overview_raw(user_id, user)
    evaluations = _evaluate_market_setups(market_overview)
    evaluations_by_symbol = {evaluation.asset["symbol"]: evaluation for evaluation in evaluations}
    signals_overview = _build_signals_overview_from_market(market_overview, user.get("level"), evaluations)
    signal_limit = _get_effective_signal_limit(user)
    signals_overview["setups"] = signals_overview["setups"][:signal_limit]
    return _build_alerts_overview_from_signals(signals_overview, user, evaluations_by_symbol)


def get_alerts_overview(user_id: int) -> dict[str, Any]:
    user = get_user(user_id)
    return _localize_payload(_get_alerts_overview_raw(user_id, user), user.get("language"))


def _get_scanner_overview_raw(user_id: int, user: dict[str, Any] | None = None) -> dict[str, Any]:
    user = user or get_user(user_id)
    watchlist = _get_user_watchlist(user)
    scanner_coins = _get_scanner_universe(user)
    scanner_limit = _get_effective_scanner_limit(user)
    market_type = user.get("market") or "spot"
    trading_style = user.get("trading_style") or "intraday"

    if MARKET_DATA_MODE == "live":
        try:
            scanner_market_overview = _build_live_market_overview(scanner_coins, market_type, trading_style)
        except Exception as error:
            print(f"Falling back to modelled scanner data: {error}")
            scanner_market_overview = _build_modelled_market_overview(user_id, scanner_coins, market_type, trading_style)
    else:
        scanner_market_overview = _build_modelled_market_overview(user_id, scanner_coins, market_type, trading_style)

    evaluations = _evaluate_market_setups(scanner_market_overview)
    evaluations_by_symbol = {evaluation.asset["symbol"]: evaluation for evaluation in evaluations}
    signals_overview = _build_signals_overview_from_market(scanner_market_overview, user.get("level"), evaluations)
    assets_by_symbol = {asset["symbol"]: asset for asset in scanner_market_overview["assets"]}
    alert_items = [
        _build_alert_item(
            setup,
            signals_overview["market_type"],
            signals_overview["trading_style"],
            signals_overview["regime"],
            evaluation=evaluations_by_symbol.get(setup["symbol"]),
        )
        for setup in signals_overview["setups"]
    ]
    alert_items.sort(key=_alert_priority_sort_key)
    alerts_by_symbol = {item["symbol"]: item for item in alert_items}
    minimum_priority = _get_effective_alerts_min_priority(user)

    candidates: list[dict[str, Any]] = []
    for index, setup in enumerate(signals_overview["setups"], start=1):
        symbol = setup["symbol"]
        asset = assets_by_symbol.get(symbol)
        alert_item = alerts_by_symbol.get(symbol)
        evaluation = evaluations_by_symbol.get(symbol)
        if not asset or not alert_item or not evaluation:
            continue

        status = _scanner_status(
            setup["status"],
            alert_item["priority"],
            alert_item.get("distance_percent"),
            setup.get("trigger_quality", setup["confidence"]),
            setup.get("setup_quality", setup["confidence"]),
            setup.get("noise_score", 50),
            signals_overview["market_type"],
            signals_overview["trading_style"],
            evaluation,
        )
        watchlist_match = symbol in watchlist
        scanner_score = _scanner_score(
            asset,
            setup,
            alert_item,
            signals_overview["regime"],
            signals_overview["market_type"],
            signals_overview["trading_style"],
            watchlist_match=watchlist_match,
            evaluation=evaluation,
        )
        urgency = _scanner_urgency(alert_item.get("distance_percent"), evaluation)
        alert_ready = bool(user.get("alerts_enabled")) and _priority_meets_minimum(alert_item["priority"], minimum_priority)
        if not _should_include_scanner_candidate(
            setup,
            alert_item,
            scanner_score,
            watchlist_match,
            signals_overview["market_type"],
            signals_overview["trading_style"],
            evaluation,
        ):
            continue

        candidates.append(
            {
                "symbol": symbol,
                "rank": index,
                "scanner_score": scanner_score,
                "status": status,
                "urgency": urgency,
                "pattern": f"{asset['setup']} | {setup['direction']}",
                "catalyst": alert_item["thesis"],
                "why_this_signal": setup.get("why_this_signal", alert_item["thesis"]),
                "confidence_explanation": _confidence_explanation(
                    evaluation.confidence,
                    evaluation.trigger_quality,
                    evaluation.setup_quality,
                    evaluation.noise_score,
                ),
                "context_note": _market_style_context_note(
                    evaluation.market_type,
                    evaluation.trading_style,
                    evaluation.regime,
                    evaluation.volatility_label,
                ),
                "trigger_plan": _scanner_trigger_plan(alert_item, setup),
                "invalidation": _scanner_invalidation(
                    status,
                    setup.get("last_price"),
                    alert_item.get("trigger_price"),
                    signals_overview["trading_style"],
                ),
                "risk_note": setup.get("risk_note", "Only act if trigger quality stays clean."),
                "watchlist_match": watchlist_match,
                "alert_ready": alert_ready,
                "last_price": setup.get("last_price"),
                "price_change_percent": setup.get("price_change_percent"),
            }
        )

    candidates.sort(key=_scanner_sort_key)
    for index, candidate in enumerate(candidates, start=1):
        candidate["rank"] = index

    visible_candidates = candidates[:scanner_limit]
    hot_count = sum(1 for candidate in candidates if candidate["status"] == "Hot")
    building_count = sum(1 for candidate in candidates if candidate["status"] == "Building")
    early_count = sum(1 for candidate in candidates if candidate["status"] == "Early")
    top_candidate = candidates[0] if candidates else None

    if hot_count >= 2 and top_candidate:
        headline = "Scanner sees multiple names close to execution. Focus the first pass on the hottest trigger, not the whole list."
        next_action = f"Work top-down: start with {top_candidate['symbol']}, then keep the second hot name as backup."
    elif hot_count == 1 and top_candidate:
        headline = "One scanner candidate stands above the rest right now."
        next_action = f"Keep {top_candidate['symbol']} in front of you and let the trigger decide the trade, not anticipation."
    elif building_count >= 1 and top_candidate:
        headline = "Scanner is finding constructive structures, but most still need proof before they deserve full attention."
        next_action = f"Queue {top_candidate['symbol']} first and use alerts to avoid watching every candle."
    else:
        headline = "Scanner is quiet enough to protect your focus. No need to force activity while structure is still early."
        next_action = "Stay selective, keep alerts armed, and wait for a cleaner quality cluster to form."

    scan_window = "5m-30m scan loop" if signals_overview["trading_style"] == "scalping" else "30m-4h scan loop"

    return {
        "market_type": signals_overview["market_type"],
        "trading_style": signals_overview["trading_style"],
        "regime": signals_overview["regime"],
        "headline": headline,
        "next_action": next_action,
        "scan_window": scan_window,
        "top_symbol": top_candidate["symbol"] if top_candidate else signals_overview.get("top_symbol"),
        "candidates": visible_candidates,
        "visible_count": len(visible_candidates),
        "universe_size": len(candidates),
        "hot_count": hot_count,
        "building_count": building_count,
        "early_count": early_count,
        "data_mode": signals_overview["data_mode"],
        "data_provider": signals_overview.get("data_provider"),
        "data_updated_at": signals_overview.get("data_updated_at"),
        "data_cached": signals_overview.get("data_cached", False),
        "data_stale": signals_overview.get("data_stale", False),
    }


def get_scanner_overview(user_id: int) -> dict[str, Any]:
    user = get_user(user_id)
    return _localize_payload(_get_scanner_overview_raw(user_id, user), user.get("language"))


def _list_alert_delivery_users() -> list[dict[str, Any]]:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT user_id
            FROM users
            WHERE alerts_enabled = 1 AND onboarding_complete = 1
            """
        ).fetchall()

    return [get_user(int(row["user_id"])) for row in rows]


def get_alert_delivery_jobs() -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for user in _list_alert_delivery_users():
        alerts_overview = _get_alerts_overview_raw(user["user_id"], user)
        filtered_items = list(alerts_overview["items"])

        if not filtered_items:
            continue

        digest_key = _build_alert_digest_key(alerts_overview, filtered_items)
        last_sent_at = _parse_iso_timestamp(user.get("last_alert_sent_at"))
        urgent_delivery = _is_urgent_alert_batch(filtered_items)
        if user.get("last_alert_digest") == digest_key:
            continue
        if last_sent_at and (now - last_sent_at).total_seconds() < ALERT_MIN_INTERVAL_SECONDS and not urgent_delivery:
            continue

        localized_overview = _localize_payload(alerts_overview, user.get("language"))

        job = {
            "user_id": user["user_id"],
            "language": user.get("language"),
            "level": user.get("level"),
            "digest_key": digest_key,
            "delivery_reason": "urgent-proximity" if urgent_delivery else "digest-changed",
            "market_type": alerts_overview["market_type"],
            "trading_style": alerts_overview["trading_style"],
            "regime": localized_overview["regime"],
            "headline": localized_overview["headline"],
            "next_action": localized_overview["next_action"],
            "active_window": localized_overview["active_window"],
            "delivery_note": localized_overview["delivery_note"],
            "delivery_status": "armed",
            "delivery_min_priority": localized_overview["delivery_min_priority"],
            "delivery_last_sent_at": alerts_overview.get("delivery_last_sent_at"),
            "delivery_next_eligible_at": alerts_overview.get("delivery_next_eligible_at"),
            "delivery_cooldown_seconds": alerts_overview.get("delivery_cooldown_seconds", 0),
            "top_symbol": alerts_overview.get("top_symbol"),
            "items": localized_overview["items"],
            "high_priority_count": sum(1 for item in filtered_items if item["priority"] == "High"),
            "medium_priority_count": sum(1 for item in filtered_items if item["priority"] == "Medium"),
            "low_priority_count": sum(1 for item in filtered_items if item["priority"] == "Low"),
            "data_mode": alerts_overview["data_mode"],
            "data_provider": alerts_overview.get("data_provider"),
            "data_updated_at": alerts_overview.get("data_updated_at"),
            "data_cached": alerts_overview.get("data_cached", False),
            "data_stale": alerts_overview.get("data_stale", False),
        }
        jobs.append(job)

    return jobs


def acknowledge_alert_delivery(user_id: int, digest_key: str) -> None:
    timestamp = _format_utc_timestamp(time.time())
    with closing(get_connection()) as connection:
        connection.execute(
            """
            UPDATE users
            SET last_alert_digest = ?, last_alert_sent_at = ?
            WHERE user_id = ?
            """,
            (digest_key, timestamp, user_id),
        )
        connection.commit()


ensure_database_schema()
