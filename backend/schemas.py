from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class HealthResponse(BaseModel):
    status: str = "ok"
    database_backend: str
    database_path: str | None = None


class WebConfigResponse(BaseModel):
    telegram_login_enabled: bool
    telegram_bot_username: str | None = None


class MarketAsset(BaseModel):
    symbol: str
    pulse_score: int
    breakout_score: int
    volatility_score: int
    bias: str
    setup: str
    signal: str
    last_price: float | None = None
    price_change_percent: float | None = None
    quote_volume: float | None = None


class MarketOverview(BaseModel):
    market_type: str
    trading_style: str
    regime: str
    sentiment_score: int
    volatility_label: str
    focus_window: str
    outlook_headline: str
    checklist: list[str]
    assets: list[MarketAsset]
    data_mode: str = "modelled"
    data_provider: str | None = None
    data_updated_at: str | None = None
    data_cached: bool = False
    data_stale: bool = False


class SignalSetup(BaseModel):
    symbol: str
    status: str
    direction: str
    confidence: int
    conviction: str
    confidence_explanation: str
    timeframe: str
    entry_plan: str
    why_this_signal: str
    context_note: str
    entry_trigger: str
    invalidation: str
    size_plan: str
    risk_note: str
    last_price: float | None = None
    price_change_percent: float | None = None


class SignalsOverview(BaseModel):
    market_type: str
    trading_style: str
    regime: str
    headline: str
    execution_bias: str
    risk_posture: str
    next_action: str
    top_symbol: str | None = None
    checklist: list[str]
    setups: list[SignalSetup]
    ready_count: int
    watch_count: int
    cool_off_count: int
    data_mode: str = "modelled"
    data_provider: str | None = None
    data_updated_at: str | None = None
    data_cached: bool = False
    data_stale: bool = False


class AlertItem(BaseModel):
    symbol: str
    alert_type: str
    direction: str
    priority: str
    trigger_price: float | None = None
    distance_percent: float | None = None
    thesis: str
    why_this_signal: str
    confidence_explanation: str
    context_note: str
    action_note: str
    invalidation: str
    risk_note: str
    last_price: float | None = None
    price_change_percent: float | None = None


class AlertsOverview(BaseModel):
    market_type: str
    trading_style: str
    regime: str
    headline: str
    next_action: str
    active_window: str
    delivery_note: str
    delivery_status: str
    delivery_min_priority: str
    delivery_last_sent_at: str | None = None
    delivery_next_eligible_at: str | None = None
    delivery_cooldown_seconds: int = 0
    top_symbol: str | None = None
    items: list[AlertItem]
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    data_mode: str = "modelled"
    data_provider: str | None = None
    data_updated_at: str | None = None
    data_cached: bool = False
    data_stale: bool = False


class ScannerCandidate(BaseModel):
    symbol: str
    rank: int
    scanner_score: int
    status: str
    urgency: str
    watchlist_match: bool = False
    pattern: str
    catalyst: str
    why_this_signal: str
    confidence_explanation: str
    context_note: str
    trigger_plan: str
    invalidation: str
    risk_note: str
    alert_ready: bool = False
    last_price: float | None = None
    price_change_percent: float | None = None


class ScannerOverview(BaseModel):
    market_type: str
    trading_style: str
    regime: str
    headline: str
    next_action: str
    scan_window: str
    top_symbol: str | None = None
    candidates: list[ScannerCandidate]
    visible_count: int
    universe_size: int
    hot_count: int
    building_count: int
    early_count: int
    data_mode: str = "modelled"
    data_provider: str | None = None
    data_updated_at: str | None = None
    data_cached: bool = False
    data_stale: bool = False


class TradePlan(BaseModel):
    symbol: str
    direction: Literal["long", "short"]
    market_type: Literal["spot", "futures"] | None = None
    trading_style: Literal["scalping", "intraday"] | None = None
    entry_price: float
    initial_stop_loss: float
    current_stop_loss: float
    tp1: float | None = None
    tp2: float | None = None
    tpf: float | None = None
    status: str
    risk_percent: float
    initial_risk_percent: float
    account_equity: float
    risk_percent_per_trade: float
    risk_amount: float = 0.0
    position_size: float = 0.0
    stop_distance_percent: float = 0.0
    tp_hit_count: int = 0
    unrealized_r_multiple: float = 0.0
    realized_r_multiple: float = 0.0
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0
    created_at: str
    updated_at: str

    @field_validator("risk_percent", "initial_risk_percent", "account_equity", "risk_percent_per_trade")
    @classmethod
    def validate_positive_risk_percent(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Risk values must be greater than 0.")
        return value

    @model_validator(mode="after")
    def validate_trade_geometry(self) -> "TradePlan":
        if self.market_type == "futures" and self.trading_style == "scalping" and self.risk_percent_per_trade > 2:
            raise ValueError("futures/scalping trades require risk_percent_per_trade <= 2.")

        stop_distance = abs(self.entry_price - self.initial_stop_loss)
        self.risk_amount = (self.account_equity * self.risk_percent_per_trade) / 100
        self.stop_distance_percent = (stop_distance / self.entry_price) * 100
        self.position_size = self.risk_amount / stop_distance if stop_distance > 0 else 0.0

        if self.direction == "long":
            if self.initial_stop_loss >= self.entry_price:
                raise ValueError("Long trades require initial_stop_loss < entry_price.")
            if self.current_stop_loss >= self.entry_price:
                raise ValueError("Long trades require current_stop_loss < entry_price.")

            if self.tp1 is not None and self.tp1 <= self.entry_price:
                raise ValueError("Long trades require tp1 > entry_price.")
            if self.tp2 is not None and self.tp2 <= self.entry_price:
                raise ValueError("Long trades require tp2 > entry_price.")
            if self.tpf is not None and self.tpf <= self.entry_price:
                raise ValueError("Long trades require tpf > entry_price.")

            if self.tp1 is not None and self.tp2 is not None and self.tp2 <= self.tp1:
                raise ValueError("Long trades require tp1 < tp2.")
            if self.tp2 is not None and self.tpf is not None and self.tpf <= self.tp2:
                raise ValueError("Long trades require tp2 < tpf.")
            if self.tp1 is not None and self.tpf is not None and self.tp2 is None and self.tpf <= self.tp1:
                raise ValueError("Long trades require tp1 < tpf.")
            return self

        if self.initial_stop_loss <= self.entry_price:
            raise ValueError("Short trades require initial_stop_loss > entry_price.")
        if self.current_stop_loss <= self.entry_price:
            raise ValueError("Short trades require current_stop_loss > entry_price.")

        if self.tp1 is not None and self.tp1 >= self.entry_price:
            raise ValueError("Short trades require tp1 < entry_price.")
        if self.tp2 is not None and self.tp2 >= self.entry_price:
            raise ValueError("Short trades require tp2 < entry_price.")
        if self.tpf is not None and self.tpf >= self.entry_price:
            raise ValueError("Short trades require tpf < entry_price.")

        if self.tp1 is not None and self.tp2 is not None and self.tp2 >= self.tp1:
            raise ValueError("Short trades require tp1 > tp2.")
        if self.tp2 is not None and self.tpf is not None and self.tpf >= self.tp2:
            raise ValueError("Short trades require tp2 > tpf.")
        if self.tp1 is not None and self.tpf is not None and self.tp2 is None and self.tpf >= self.tp1:
            raise ValueError("Short trades require tp1 > tpf.")
        return self


class TradeManagementEvent(BaseModel):
    symbol: str
    event_type: Literal["tp1_hit", "tp2_hit", "tpf_hit", "sl_moved", "stopped", "invalidated"]
    direction: Literal["long", "short"]
    status: str
    current_price: float
    previous_stop_loss: float | None = None
    current_stop_loss: float | None = None
    reference_price: float | None = None
    detail: str | None = None


class TradeManagementSimulationPayload(BaseModel):
    trade_id: str | None = None
    previous_plan: TradePlan
    current_plan: TradePlan
    current_price: float
    invalidated: bool = False


class TradeManagementNotificationJob(BaseModel):
    user_id: int
    language: Literal["fr", "en", "es"] | None = None
    level: Literal["beginner", "medium", "pro"] | None = None
    event_key: str
    event_type: Literal["tp1_hit", "tp2_hit", "tpf_hit", "sl_moved", "stopped", "invalidated"]
    symbol: str
    message: str
    current_price: float
    created_at: str


class TradeManagementEventAck(BaseModel):
    event_key: str


class TradePlanCreatePayload(BaseModel):
    symbol: str
    direction: Literal["long", "short"]
    entry_price: float
    initial_stop_loss: float
    current_stop_loss: float | None = None
    tp1: float | None = None
    tp2: float | None = None
    tpf: float | None = None
    status: str = "active"
    market_type: Literal["spot", "futures"]
    trading_style: Literal["scalping", "intraday"]
    account_equity: float
    risk_percent_per_trade: float


class TradePlanSimulatePayload(BaseModel):
    current_price: float
    current_stop_loss: float | None = None
    status: str | None = None
    tp_hit_count: int | None = None


class TradeJournalEntry(BaseModel):
    trade_id: str
    symbol: str
    direction: Literal["long", "short"]
    archetype: str
    market_type: Literal["spot", "futures"]
    trading_style: Literal["scalping", "intraday"]
    status: Literal["open", "closed"]
    entry_price: float
    initial_stop_loss: float
    exit_price: float | None = None
    exit_reason: str | None = None
    realized_r_multiple: float
    tp_hit_count: int = 0
    stopped_after_tp: bool = False
    feedback_label: Literal["good", "neutral", "bad"] | None = None
    created_at: str
    closed_at: str | None = None

    @model_validator(mode="after")
    def validate_trade_journal_entry(self) -> "TradeJournalEntry":
        if self.status == "open":
            if self.exit_price is not None or self.exit_reason is not None or self.closed_at is not None:
                raise ValueError("Open trades must not define exit_price, exit_reason, or closed_at.")
            return self

        if self.exit_price is None or self.exit_reason is None or self.closed_at is None:
            raise ValueError("Closed trades require exit_price, exit_reason, and closed_at.")

        created_at = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        closed_at = datetime.fromisoformat(self.closed_at.replace("Z", "+00:00"))
        if closed_at < created_at:
            raise ValueError("closed_at must be greater than or equal to created_at.")
        return self


class ArchetypePerformanceStats(BaseModel):
    total_trades: int = 0
    win_rate: float = 0.0
    average_r_multiple: float = 0.0


class TradeJournalStats(BaseModel):
    total_trades: int = 0
    win_rate: float = 0.0
    average_r_multiple: float = 0.0
    average_tp_hit_count: float = 0.0
    stopped_after_tp_rate: float = 0.0
    performance_by_archetype: dict[str, ArchetypePerformanceStats] = Field(default_factory=dict)


class AlertDeliveryJob(AlertsOverview):
    user_id: int
    language: Literal["fr", "en", "es"] | None = None
    level: Literal["beginner", "medium", "pro"] | None = None
    digest_key: str
    delivery_reason: str | None = None


class AlertDeliveryAck(BaseModel):
    digest_key: str


class UserState(BaseModel):
    user_id: int
    intro_seen: bool = False
    language: Literal["fr", "en", "es"] | None = None
    level: Literal["beginner", "medium", "pro"] | None = None
    scanner_limit: int | None = None
    market: Literal["spot", "futures"] | None = None
    trading_style: Literal["scalping", "intraday"] | None = None
    coins: list[str] = Field(default_factory=list)
    alerts_enabled: bool = False
    alerts_min_priority: Literal["high", "medium", "low"] = "high"
    onboarding_complete: bool = False
    active_message_id: int | None = None
    # Calculé côté service (non stocké en base) — défaut "" pour éviter ValidationError
    next_step: str = ""


class UserPatch(BaseModel):
    intro_seen: bool | None = None
    language: Literal["fr", "en", "es"] | None = None
    level: Literal["beginner", "medium", "pro"] | None = None
    scanner_limit: int | None = None
    market: Literal["spot", "futures"] | None = None
    trading_style: Literal["scalping", "intraday"] | None = None
    coins: list[str] | None = None
    alerts_enabled: bool | None = None
    alerts_min_priority: Literal["high", "medium", "low"] | None = None
    active_message_id: int | None = None

    @field_validator("coins")
    @classmethod
    def validate_coins(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value

        normalized: list[str] = []
        seen: set[str] = set()

        for item in value:
            symbol = item.strip().upper()

            if not symbol:
                raise ValueError("Coins cannot contain empty symbols.")

            if symbol not in seen:
                normalized.append(symbol)
                seen.add(symbol)

        if len(normalized) > 3:
            raise ValueError("Coins can contain at most 3 symbols.")

        return normalized


class TelegramAuthPayload(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str
