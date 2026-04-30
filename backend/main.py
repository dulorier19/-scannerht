import hmac
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth import (
    clear_authenticated_session,
    require_authenticated_user_id,
    require_internal_api_key,
    set_authenticated_session,
    verify_telegram_login,
)
from .config import BOT_TOKEN, BOT_USERNAME, CORS_ORIGINS, DATABASE_BACKEND, DB_PATH, HEALTH_DETAILS_ENABLED, INTERNAL_API_KEY
from .schemas import (
    AlertDeliveryAck,
    AlertDeliveryJob,
    AlertsOverview,
    HealthResponse,
    MarketOverview,
    ScannerOverview,
    SignalsOverview,
    TelegramAuthPayload,
    TradePlan,
    TradePlanCreatePayload,
    TradePlanSimulatePayload,
    TradeManagementEventAck,
    TradeManagementNotificationJob,
    TradeManagementSimulationPayload,
    UserPatch,
    UserState,
    WebConfigResponse,
)
from .services import (
    acknowledge_alert_delivery,
    acknowledge_trade_management_event,
    calculate_trade_journal_stats,
    get_alert_delivery_jobs,
    get_alerts_overview,
    get_market_overview,
    get_pending_trade_events,
    get_scanner_overview,
    get_signals_overview,
    get_trade_management_jobs,
    get_trade_journal_by_user,
    get_trade_plans_by_user,
    get_user,
    reset_user,
    save_trade_plan,
    save_user,
    simulate_trade_management,
    update_trade_plan,
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
ASSETS_DIR = WEB_DIR / "assets"

app = FastAPI(
    title="ScannerHT Backend",
    version="0.1.0",
    description="Shared Python backend for the Telegram bot and future web app.",
)

allow_all_origins = CORS_ORIGINS == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else CORS_ORIGINS,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
_TRADE_SIMULATE_RATE_LIMIT_CACHE: dict[str, list[float]] = {}


@app.middleware("http")
async def enforce_internal_api_key(request: Request, call_next):
    if request.url.path.startswith("/api/internal/"):
        provided_key = request.headers.get("x-internal-api-key", "")
        if not INTERNAL_API_KEY or not provided_key or not hmac.compare_digest(provided_key, INTERNAL_API_KEY):
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Internal API key required."})
    return await call_next(request)


def _serialize_trade_plan_debug(plan: dict[str, Any]) -> dict[str, object]:
    risk_percent_per_trade = float(plan.get("risk_percent_per_trade", 0.0) or 0.0)
    realized_r_multiple = float(plan.get("realized_r_multiple", 0.0) or 0.0)
    unrealized_r_multiple = float(plan.get("unrealized_r_multiple", 0.0) or 0.0)
    entry_price = float(plan["entry_price"])
    initial_stop_loss = float(plan["initial_stop_loss"])
    risk_amount = float(plan.get("risk_amount", 0.0) or 0.0)
    current_price = plan.get("current_price")
    account_equity = float(plan["account_equity"]) if "account_equity" in plan and plan["account_equity"] is not None else None
    if account_equity is None and risk_percent_per_trade > 0:
        account_equity = risk_amount / (risk_percent_per_trade / 100)
    stop_distance_percent = 0.0
    if entry_price > 0:
        stop_distance_percent = (abs(entry_price - initial_stop_loss) / entry_price) * 100

    return {
        "id": plan["id"],
        "symbol": plan["symbol"],
        "direction": plan["direction"],
        "status": plan["status"],
        "entry_price": entry_price,
        "current_price": float(current_price) if isinstance(current_price, (int, float)) else None,
        "account_equity": account_equity,
        "initial_stop_loss": initial_stop_loss,
        "current_stop_loss": plan["current_stop_loss"],
        "tp1": plan.get("tp1"),
        "tp2": plan.get("tp2"),
        "tpf": plan.get("tpf"),
        "risk_percent_per_trade": risk_percent_per_trade,
        "risk_amount": risk_amount,
        "position_size": float(plan.get("position_size", 0.0) or 0.0),
        "stop_distance_percent": stop_distance_percent,
        "realized_pnl_amount": realized_r_multiple * risk_amount,
        "realized_pnl_percent": realized_r_multiple * risk_percent_per_trade,
        "unrealized_pnl_amount": unrealized_r_multiple * risk_amount,
        "unrealized_pnl_percent": unrealized_r_multiple * risk_percent_per_trade,
        "created_at": plan["created_at"],
        "updated_at": plan["updated_at"],
    }


def _serialize_trade_journal_debug(entry: dict[str, Any], plans_by_id: dict[str, dict[str, Any]]) -> dict[str, object]:
    plan = plans_by_id.get(entry["trade_id"])
    risk_amount = float(plan.get("risk_amount", 0.0) or 0.0) if plan else 0.0
    risk_percent_per_trade = float(plan.get("risk_percent_per_trade", 0.0) or 0.0) if plan else 0.0
    realized_r_multiple = float(entry["realized_r_multiple"])
    realized_pnl_amount = realized_r_multiple * risk_amount if plan else None
    realized_pnl_percent = realized_r_multiple * risk_percent_per_trade if plan else None

    return {
        "trade_id": entry["trade_id"],
        "symbol": entry["symbol"],
        "direction": entry["direction"],
        "archetype": entry["archetype"],
        "market_type": entry["market_type"],
        "trading_style": entry["trading_style"],
        "entry_price": entry["entry_price"],
        "exit_price": entry["exit_price"],
        "exit_reason": entry["exit_reason"],
        "realized_r_multiple": realized_r_multiple,
        "realized_pnl_amount": realized_pnl_amount,
        "realized_pnl_percent": realized_pnl_percent,
        "tp_hit_count": entry["tp_hit_count"],
        "stopped_after_tp": entry["stopped_after_tp"],
        "feedback_label": entry["feedback_label"],
        "created_at": entry["created_at"],
        "closed_at": entry["closed_at"],
    }


def _build_trade_plan_model_from_record(plan: dict[str, Any]) -> TradePlan:
    risk_percent_per_trade = float(plan.get("risk_percent_per_trade", 0.0) or 0.0)
    risk_amount = float(plan.get("risk_amount", 0.0) or 0.0)
    account_equity = risk_amount / (risk_percent_per_trade / 100) if risk_percent_per_trade > 0 else None
    if account_equity is None or account_equity <= 0:
        raise ValueError("Trade plan requires inferable account_equity from risk_amount and risk_percent_per_trade.")

    return TradePlan(
        symbol=plan["symbol"],
        direction=plan["direction"],
        market_type=plan.get("market_type"),
        trading_style=plan.get("trading_style"),
        entry_price=float(plan["entry_price"]),
        initial_stop_loss=float(plan["initial_stop_loss"]),
        current_stop_loss=float(plan["current_stop_loss"]),
        tp1=plan.get("tp1"),
        tp2=plan.get("tp2"),
        tpf=plan.get("tpf"),
        status=plan["status"],
        risk_percent=float(plan["risk_percent"]),
        initial_risk_percent=float(plan["initial_risk_percent"]),
        account_equity=account_equity,
        risk_percent_per_trade=risk_percent_per_trade,
        risk_amount=float(plan.get("risk_amount", 0.0) or 0.0),
        position_size=float(plan.get("position_size", 0.0) or 0.0),
        tp_hit_count=int(plan.get("tp_hit_count", 0) or 0),
        unrealized_r_multiple=float(plan.get("unrealized_r_multiple", 0.0) or 0.0),
        realized_r_multiple=float(plan.get("realized_r_multiple", 0.0) or 0.0),
        created_at=plan["created_at"],
        updated_at=plan["updated_at"],
    )


def _enforce_trade_simulate_rate_limit(rate_limit_key: str) -> None:
    now = time.monotonic()
    window_seconds = 5.0
    max_requests = 3
    timestamps = [timestamp for timestamp in _TRADE_SIMULATE_RATE_LIMIT_CACHE.get(rate_limit_key, []) if now - timestamp <= window_seconds]
    if len(timestamps) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limited",
                "message": "Too many simulate requests for this trade. Wait a few seconds before retrying.",
                "retry_after_seconds": 5,
                "limit": 3,
                "window_seconds": 5,
            },
        )
    timestamps.append(now)
    _TRADE_SIMULATE_RATE_LIMIT_CACHE[rate_limit_key] = timestamps


@app.get("/", include_in_schema=False)
def serve_web_app() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(
        database_backend=DATABASE_BACKEND,
        database_path=str(DB_PATH) if HEALTH_DETAILS_ENABLED else None,
    )


@app.get("/api/web/config", response_model=WebConfigResponse)
def web_config() -> WebConfigResponse:
    enabled = bool(BOT_TOKEN and BOT_USERNAME)
    return WebConfigResponse(
        telegram_login_enabled=enabled,
        telegram_bot_username=BOT_USERNAME or None,
    )


@app.post("/api/auth/telegram", response_model=UserState)
def telegram_auth(payload: TelegramAuthPayload, response: Response) -> UserState:
    try:
        telegram_user = verify_telegram_login(payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    set_authenticated_session(response, telegram_user)
    return UserState(**get_user(int(telegram_user["id"])))


@app.post("/api/auth/logout")
def logout(response: Response) -> dict[str, bool]:
    clear_authenticated_session(response)
    return {"ok": True}


@app.get("/api/web/me", response_model=UserState)
def read_current_user(request: Request) -> UserState:
    user_id = require_authenticated_user_id(request)
    return UserState(**get_user(user_id))


@app.patch("/api/web/me", response_model=UserState)
def patch_current_user(request: Request, payload: UserPatch) -> UserState:
    user_id = require_authenticated_user_id(request)

    try:
        user = save_user(user_id, payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return UserState(**user)


@app.post("/api/web/me/reset", response_model=UserState)
def reset_current_user(request: Request) -> UserState:
    user_id = require_authenticated_user_id(request)
    return UserState(**reset_user(user_id))


@app.get("/api/web/market", response_model=MarketOverview)
def read_current_market(request: Request) -> MarketOverview:
    user_id = require_authenticated_user_id(request)
    return MarketOverview(**get_market_overview(user_id))


@app.get("/api/web/signals", response_model=SignalsOverview)
def read_current_signals(request: Request) -> SignalsOverview:
    user_id = require_authenticated_user_id(request)
    return SignalsOverview(**get_signals_overview(user_id))


@app.get("/api/web/alerts", response_model=AlertsOverview)
def read_current_alerts(request: Request) -> AlertsOverview:
    user_id = require_authenticated_user_id(request)
    return AlertsOverview(**get_alerts_overview(user_id))


@app.get("/api/web/scanner", response_model=ScannerOverview)
def read_current_scanner(request: Request) -> ScannerOverview:
    user_id = require_authenticated_user_id(request)
    return ScannerOverview(**get_scanner_overview(user_id))


@app.get("/api/users/{user_id}", response_model=UserState)
def read_user(user_id: int, request: Request) -> UserState:
    require_internal_api_key(request)
    return UserState(**get_user(user_id))


@app.patch("/api/users/{user_id}", response_model=UserState)
def patch_user(user_id: int, payload: UserPatch, request: Request) -> UserState:
    require_internal_api_key(request)
    try:
        user = save_user(user_id, payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return UserState(**user)


@app.post("/api/users/{user_id}/reset", response_model=UserState)
def reset_user_state(user_id: int, request: Request) -> UserState:
    require_internal_api_key(request)
    return UserState(**reset_user(user_id))


@app.get("/api/users/{user_id}/market", response_model=MarketOverview)
def read_user_market(user_id: int, request: Request) -> MarketOverview:
    require_internal_api_key(request)
    return MarketOverview(**get_market_overview(user_id))


@app.get("/api/users/{user_id}/signals", response_model=SignalsOverview)
def read_user_signals(user_id: int, request: Request) -> SignalsOverview:
    require_internal_api_key(request)
    return SignalsOverview(**get_signals_overview(user_id))


@app.get("/api/users/{user_id}/alerts", response_model=AlertsOverview)
def read_user_alerts(user_id: int, request: Request) -> AlertsOverview:
    require_internal_api_key(request)
    return AlertsOverview(**get_alerts_overview(user_id))


@app.get("/api/users/{user_id}/scanner", response_model=ScannerOverview)
def read_user_scanner(user_id: int, request: Request) -> ScannerOverview:
    require_internal_api_key(request)
    return ScannerOverview(**get_scanner_overview(user_id))


@app.get("/api/internal/alerts/jobs", response_model=list[AlertDeliveryJob])
def read_alert_delivery_jobs(request: Request) -> list[AlertDeliveryJob]:
    require_internal_api_key(request)
    return [AlertDeliveryJob(**job) for job in get_alert_delivery_jobs()]


@app.post("/api/internal/alerts/{user_id}/ack")
def ack_alert_delivery(user_id: int, payload: AlertDeliveryAck, request: Request) -> dict[str, bool]:
    require_internal_api_key(request)
    acknowledge_alert_delivery(user_id, payload.digest_key)
    return {"ok": True}


@app.post("/api/internal/trades/{user_id}/simulate", response_model=list[TradeManagementNotificationJob])
def simulate_trade_management_notifications(
    user_id: int,
    payload: TradeManagementSimulationPayload,
    request: Request,
) -> list[TradeManagementNotificationJob]:
    require_internal_api_key(request)
    rate_limit_key = payload.trade_id or f"user:{user_id}:symbol:{payload.current_plan.symbol}"
    _enforce_trade_simulate_rate_limit(rate_limit_key)
    jobs = simulate_trade_management(
        user_id,
        payload.previous_plan,
        payload.current_plan,
        payload.current_price,
        trade_id=payload.trade_id,
        invalidated=payload.invalidated,
    )
    return [TradeManagementNotificationJob(**job) for job in jobs]


@app.get("/api/internal/trades/jobs", response_model=list[TradeManagementNotificationJob])
def read_trade_management_jobs(request: Request) -> list[TradeManagementNotificationJob]:
    require_internal_api_key(request)
    return [TradeManagementNotificationJob(**job) for job in get_trade_management_jobs()]


@app.post("/api/internal/trades/{user_id}/ack")
def ack_trade_management_notification(
    user_id: int,
    payload: TradeManagementEventAck,
    request: Request,
) -> dict[str, bool]:
    require_internal_api_key(request)
    acknowledge_trade_management_event(user_id, payload.event_key)
    return {"ok": True}


@app.get("/api/internal/trades/events")
def read_trade_events(request: Request, acknowledged: bool | None = None) -> list[dict[str, object]]:
    require_internal_api_key(request)
    return [dict(event) for event in get_pending_trade_events(acknowledged=acknowledged)]


@app.get("/api/internal/trades/{user_id}/journal")
def read_trade_journal(user_id: int, request: Request) -> dict[str, object]:
    require_internal_api_key(request)

    entries = get_trade_journal_by_user(user_id)
    stats = calculate_trade_journal_stats(entries)
    plans_by_id = {plan["id"]: plan for plan in get_trade_plans_by_user(user_id)}

    return {
        "entries": [_serialize_trade_journal_debug(entry, plans_by_id) for entry in entries],
        "stats": stats,
    }


@app.post("/api/internal/trades/{user_id}/plans")
def create_trade_plan(user_id: int, payload: TradePlanCreatePayload, request: Request) -> dict[str, object]:
    require_internal_api_key(request)
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    risk_percent_per_trade = float(payload.risk_percent_per_trade)
    plan = TradePlan(
        symbol=payload.symbol,
        direction=payload.direction,
        market_type=payload.market_type,
        trading_style=payload.trading_style,
        entry_price=payload.entry_price,
        initial_stop_loss=payload.initial_stop_loss,
        current_stop_loss=payload.current_stop_loss if payload.current_stop_loss is not None else payload.initial_stop_loss,
        tp1=payload.tp1,
        tp2=payload.tp2,
        tpf=payload.tpf,
        status=payload.status,
        risk_percent=risk_percent_per_trade,
        initial_risk_percent=risk_percent_per_trade,
        account_equity=payload.account_equity,
        risk_percent_per_trade=risk_percent_per_trade,
        created_at=timestamp,
        updated_at=timestamp,
    )
    return _serialize_trade_plan_debug(save_trade_plan(user_id, plan))


@app.post("/api/internal/trades/{user_id}/plans/{trade_id}/simulate")
def simulate_existing_trade_plan(
    user_id: int,
    trade_id: str,
    payload: TradePlanSimulatePayload,
    request: Request,
) -> dict[str, object]:
    require_internal_api_key(request)
    _enforce_trade_simulate_rate_limit(trade_id)

    plans_by_id = {plan["id"]: plan for plan in get_trade_plans_by_user(user_id)}
    previous_plan_record = plans_by_id.get(trade_id)
    if previous_plan_record is None:
        raise HTTPException(status_code=404, detail="Trade plan not found.")

    try:
        previous_plan = _build_trade_plan_model_from_record(previous_plan_record)
        current_plan = TradePlan(
            **{
                **previous_plan.model_dump(),
                "current_stop_loss": payload.current_stop_loss
                if payload.current_stop_loss is not None
                else previous_plan.current_stop_loss,
                "status": payload.status if payload.status is not None else previous_plan.status,
                "tp_hit_count": payload.tp_hit_count if payload.tp_hit_count is not None else previous_plan.tp_hit_count,
                "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )
        jobs = simulate_trade_management(
            user_id,
            previous_plan,
            current_plan,
            payload.current_price,
            trade_id=trade_id,
        )
        persisted_plan = update_trade_plan(
            trade_id,
            {
                "current_stop_loss": current_plan.current_stop_loss,
                "status": current_plan.status,
                "tp_hit_count": current_plan.tp_hit_count,
            },
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {
        "plan": _serialize_trade_plan_debug(persisted_plan),
        "events": [TradeManagementNotificationJob(**job).model_dump() for job in jobs],
    }


@app.get("/api/internal/trades/{user_id}/plans")
def read_trade_plans(user_id: int, request: Request) -> list[dict[str, object]]:
    require_internal_api_key(request)
    return [_serialize_trade_plan_debug(plan) for plan in get_trade_plans_by_user(user_id)]


@app.get("/api/internal/trades/{user_id}/debug")
def read_trade_debug(user_id: int, request: Request) -> dict[str, object]:
    require_internal_api_key(request)

    plans = get_trade_plans_by_user(user_id)
    events_pending = [dict(event) for event in get_pending_trade_events(user_id=user_id, acknowledged=False)]
    events_acknowledged = [dict(event) for event in get_pending_trade_events(user_id=user_id, acknowledged=True)]
    journal_entries = get_trade_journal_by_user(user_id)
    stats = calculate_trade_journal_stats(journal_entries)
    plans_by_id = {plan["id"]: plan for plan in plans}

    serialized_plans = [_serialize_trade_plan_debug(plan) for plan in plans]
    serialized_journal = [_serialize_trade_journal_debug(entry, plans_by_id) for entry in journal_entries]

    total_realized_pnl_amount = sum(
        float(entry["realized_pnl_amount"])
        for entry in serialized_journal
        if entry["realized_pnl_amount"] is not None
    )
    total_realized_pnl_percent = sum(
        float(entry["realized_pnl_percent"])
        for entry in serialized_journal
        if entry["realized_pnl_percent"] is not None
    )
    active_plans_count = sum(
        1
        for plan in serialized_plans
        if str(plan["status"]).strip().lower() not in {"closed", "stopped", "invalidated", "completed"}
    )

    return {
        "plans": serialized_plans,
        "events_pending": events_pending,
        "events_acknowledged": events_acknowledged,
        "journal": serialized_journal,
        "stats": stats,
        "summary": {
            "active_plans_count": active_plans_count,
            "pending_events_count": len(events_pending),
            "acknowledged_events_count": len(events_acknowledged),
            "closed_trades_count": len(serialized_journal),
            "total_realized_pnl_amount": total_realized_pnl_amount,
            "total_realized_pnl_percent": total_realized_pnl_percent,
            "average_r_multiple": stats["average_r_multiple"],
            "win_rate": stats["win_rate"],
        },
    }
