#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
import types
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import dotenv  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    shim = types.ModuleType("dotenv")
    shim.load_dotenv = lambda *args, **kwargs: False
    sys.modules["dotenv"] = shim

try:
    import pydantic  # type: ignore  # noqa: F401
    PYDANTIC_SHIM = False
except ModuleNotFoundError:
    PYDANTIC_SHIM = True
    shim = types.ModuleType("pydantic")

    class BaseModel:
        def __init__(self, **kwargs):
            annotations = getattr(self.__class__, "__annotations__", {})
            for field_name in annotations:
                if field_name in kwargs:
                    value = kwargs[field_name]
                else:
                    value = getattr(self.__class__, field_name, None)
                setattr(self, field_name, value)

    def Field(default=None, default_factory=None, **kwargs):
        if default_factory is not None:
            return default_factory()
        return default

    def field_validator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def model_validator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    shim.BaseModel = BaseModel
    shim.Field = Field
    shim.field_validator = field_validator
    shim.model_validator = model_validator
    sys.modules["pydantic"] = shim

from backend.schemas import TradeJournalEntry, TradePlan  # noqa: E402
from backend.services import (  # noqa: E402
    _TRADE_MANAGEMENT_JOB_QUEUE,
    acknowledge_trade_management_event,
    acknowledge_trade_event,
    adaptive_setup_score_adjustment,
    calculate_trade_plan_performance,
    calculate_trade_journal_stats,
    detect_trade_management_events,
    format_trade_management_event_message,
    get_connection,
    get_trade_management_jobs,
    get_pending_trade_events,
    get_trade_journal_by_user,
    get_trade_plans_by_user,
    save_trade_event,
    save_trade_journal_entry,
    save_trade_plan,
    save_user,
    simulate_trade_management,
    update_trade_plan,
    update_trade_plan_stop_loss,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_close(actual: float, expected: float, message: str, tolerance: float = 1e-9) -> None:
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        raise AssertionError(f"{message}. Expected {expected}, got {actual}.")


def make_trade_plan(direction: str, **overrides: float | int | str | None) -> TradePlan:
    payload: dict[str, float | int | str | None]
    if direction == "long":
        payload = {
            "symbol": "BTC",
            "direction": "long",
            "market_type": "spot",
            "trading_style": "intraday",
            "entry_price": 100.0,
            "initial_stop_loss": 95.0,
            "current_stop_loss": 95.0,
            "tp1": 105.0,
            "tp2": 110.0,
            "tpf": 120.0,
            "status": "open",
            "risk_percent": 1.0,
            "initial_risk_percent": 1.0,
            "account_equity": 10_000.0,
            "risk_percent_per_trade": 1.0,
            "tp_hit_count": 0,
            "created_at": "2026-04-26T00:00:00Z",
            "updated_at": "2026-04-26T00:00:00Z",
        }
    else:
        payload = {
            "symbol": "ETH",
            "direction": "short",
            "market_type": "spot",
            "trading_style": "intraday",
            "entry_price": 100.0,
            "initial_stop_loss": 105.0,
            "current_stop_loss": 105.0,
            "tp1": 95.0,
            "tp2": 90.0,
            "tpf": 80.0,
            "status": "open",
            "risk_percent": 1.0,
            "initial_risk_percent": 1.0,
            "account_equity": 10_000.0,
            "risk_percent_per_trade": 1.0,
            "tp_hit_count": 0,
            "created_at": "2026-04-26T00:00:00Z",
            "updated_at": "2026-04-26T00:00:00Z",
        }

    payload.update(overrides)
    plan = TradePlan(**payload)

    if PYDANTIC_SHIM:
        plan.risk_percent = TradePlan.validate_positive_risk_percent(plan.risk_percent)
        plan.initial_risk_percent = TradePlan.validate_positive_risk_percent(plan.initial_risk_percent)
        plan.account_equity = TradePlan.validate_positive_risk_percent(plan.account_equity)
        plan.risk_percent_per_trade = TradePlan.validate_positive_risk_percent(plan.risk_percent_per_trade)
        plan = TradePlan.validate_trade_geometry(plan)

    return plan


def make_trade_journal_entry(**overrides: float | int | str | bool | None) -> TradeJournalEntry:
    payload: dict[str, float | int | str | bool | None] = {
        "trade_id": "journal-default",
        "symbol": "BTC",
        "direction": "long",
        "archetype": "Trend continuation",
        "market_type": "spot",
        "trading_style": "intraday",
        "status": "closed",
        "entry_price": 100.0,
        "initial_stop_loss": 95.0,
        "exit_price": 110.0,
        "exit_reason": "tp1",
        "realized_r_multiple": 2.0,
        "tp_hit_count": 1,
        "stopped_after_tp": False,
        "feedback_label": "good",
        "created_at": "2026-04-26T00:00:00Z",
        "closed_at": "2026-04-26T01:00:00Z",
    }
    payload.update(overrides)
    entry = TradeJournalEntry(**payload)

    if PYDANTIC_SHIM:
        entry = TradeJournalEntry.validate_trade_journal_entry(entry)

    return entry


def assert_rejected(builder, message: str) -> None:
    try:
        builder()
    except ValueError:
        return
    raise AssertionError(message)


def cleanup_db_trade_test_data(user_id: int) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM trade_events WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM trade_journal WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM trade_plans WHERE user_id = ?", (user_id,))
        connection.commit()
    _TRADE_MANAGEMENT_JOB_QUEUE.pop(user_id, None)


def run_tradeplan_schema_smoke() -> None:
    long_plan = make_trade_plan("long")
    short_plan = make_trade_plan("short")

    assert_true(long_plan.direction == "long", "TradePlan long should keep direction=long.")
    assert_true(short_plan.direction == "short", "TradePlan short should keep direction=short.")
    assert_true(long_plan.current_stop_loss == long_plan.initial_stop_loss, "Long plan should start with initial SL.")
    assert_true(short_plan.current_stop_loss == short_plan.initial_stop_loss, "Short plan should start with initial SL.")
    assert_close(long_plan.risk_amount, 100.0, "Long TradePlan risk amount should be derived from equity and risk percent")
    assert_close(long_plan.position_size, 20.0, "Long TradePlan position size should match risk sizing formula")
    assert_close(long_plan.stop_distance_percent, 5.0, "Long TradePlan stop distance percent should be correct")
    print("PASS trade plan schema: valid long + short plans")

    assert_rejected(
        lambda: make_trade_plan("long", initial_stop_loss=100.0),
        "TradePlan long should reject initial_stop_loss >= entry_price.",
    )
    assert_rejected(
        lambda: make_trade_plan("short", initial_stop_loss=100.0),
        "TradePlan short should reject initial_stop_loss <= entry_price.",
    )
    print("PASS trade plan schema: invalid stop geometry rejected")

    long_order_plan = make_trade_plan("long", tp1=104.0, tp2=108.0, tpf=115.0)
    short_order_plan = make_trade_plan("short", tp1=96.0, tp2=91.0, tpf=85.0)
    assert_true(long_order_plan.tp1 < long_order_plan.tp2 < long_order_plan.tpf, "Long TP order should stay tp1 < tp2 < tpf.")
    assert_true(short_order_plan.tp1 > short_order_plan.tp2 > short_order_plan.tpf, "Short TP order should stay tp1 > tp2 > tpf.")
    print("PASS trade plan schema: TP order valid for long + short")

    assert_rejected(
        lambda: make_trade_plan("long", account_equity=0.0),
        "TradePlan should reject account_equity <= 0.",
    )
    assert_rejected(
        lambda: make_trade_plan("long", risk_percent_per_trade=0.0),
        "TradePlan should reject risk_percent_per_trade <= 0.",
    )
    assert_rejected(
        lambda: make_trade_plan("long", market_type="futures", trading_style="scalping", risk_percent_per_trade=2.01),
        "TradePlan should reject risk_percent_per_trade > 2 for futures/scalping.",
    )
    futures_scalping_plan = make_trade_plan("long", market_type="futures", trading_style="scalping", risk_percent_per_trade=2.0)
    assert_close(futures_scalping_plan.risk_percent_per_trade, 2.0, "TradePlan should accept 2% max risk for futures/scalping")
    assert_rejected(
        lambda: make_trade_plan("long", market_type="futures", trading_style="scalping", risk_percent_per_trade=5.0),
        "TradePlan should reject 5% risk for futures/scalping.",
    )
    print("PASS trade plan schema: risk model validations are enforced")


def run_stop_loss_smoke() -> None:
    long_plan = make_trade_plan("long")
    short_plan = make_trade_plan("short")

    protected_long_before_tp1 = update_trade_plan_stop_loss(
        direction=long_plan.direction,
        entry_price=long_plan.entry_price,
        initial_stop_loss=long_plan.initial_stop_loss,
        current_stop_loss=97.0,
        current_price=104.0,
        tp_hit_count=0,
        noise_level="medium",
    )
    assert_close(protected_long_before_tp1, 97.0, "Before TP1, long SL should not become less protective")

    protected_short_before_tp1 = update_trade_plan_stop_loss(
        direction=short_plan.direction,
        entry_price=short_plan.entry_price,
        initial_stop_loss=short_plan.initial_stop_loss,
        current_stop_loss=103.0,
        current_price=96.0,
        tp_hit_count=0,
        noise_level="medium",
    )
    assert_close(protected_short_before_tp1, 103.0, "Before TP1, short SL should not become less protective")
    print("PASS stop loss: before TP1 never becomes less protective")

    long_after_tp1 = update_trade_plan_stop_loss(
        direction=long_plan.direction,
        entry_price=long_plan.entry_price,
        initial_stop_loss=long_plan.initial_stop_loss,
        current_stop_loss=long_plan.current_stop_loss,
        current_price=110.0,
        tp_hit_count=1,
        noise_level="low",
    )
    assert_true(long_after_tp1 >= long_plan.initial_stop_loss, "After TP1, long SL must not re-open initial risk.")
    assert_true(long_after_tp1 <= long_plan.entry_price, "After TP1, long SL should stay near or under entry.")
    assert_close(long_after_tp1, 100.0, "After TP1, long SL should move to breakeven guard")

    short_after_tp1 = update_trade_plan_stop_loss(
        direction=short_plan.direction,
        entry_price=short_plan.entry_price,
        initial_stop_loss=short_plan.initial_stop_loss,
        current_stop_loss=short_plan.current_stop_loss,
        current_price=90.0,
        tp_hit_count=1,
        noise_level="medium",
    )
    assert_true(short_after_tp1 <= short_plan.initial_stop_loss, "After TP1, short SL must not re-open initial risk.")
    assert_true(short_after_tp1 >= short_plan.entry_price, "After TP1, short SL should stay near or above entry.")
    assert_close(short_after_tp1, 100.0, "After TP1, short SL should move to breakeven guard")
    print("PASS stop loss: after TP1 protects without increasing initial risk")

    long_after_tp2 = update_trade_plan_stop_loss(
        direction=long_plan.direction,
        entry_price=long_plan.entry_price,
        initial_stop_loss=long_plan.initial_stop_loss,
        current_stop_loss=long_after_tp1,
        current_price=110.0,
        tp_hit_count=2,
        noise_level="low",
    )
    short_after_tp2 = update_trade_plan_stop_loss(
        direction=short_plan.direction,
        entry_price=short_plan.entry_price,
        initial_stop_loss=short_plan.initial_stop_loss,
        current_stop_loss=short_after_tp1,
        current_price=90.0,
        tp_hit_count=2,
        noise_level="medium",
    )
    assert_true(long_after_tp2 > long_after_tp1, "After TP2, long SL should protect more than after TP1.")
    assert_true(short_after_tp2 < short_after_tp1, "After TP2, short SL should protect more than after TP1.")
    print("PASS stop loss: after TP2 protection is stronger")

    low_distance = 110.0 - long_after_tp2
    medium_distance = short_after_tp1 - 90.0
    high_short_stop = update_trade_plan_stop_loss(
        direction="short",
        entry_price=100.0,
        initial_stop_loss=105.0,
        current_stop_loss=100.0,
        current_price=90.0,
        tp_hit_count=2,
        noise_level="high",
    )
    high_distance = high_short_stop - 90.0

    assert_true(low_distance + 1e-9 >= 110.0 * 0.0035, "Low-noise minimum distance should be respected.")
    assert_true(medium_distance + 1e-9 >= 90.0 * 0.0050, "Medium-noise minimum distance should be respected.")
    assert_true(high_distance + 1e-9 >= 90.0 * 0.0065, "High-noise minimum distance should be respected.")
    print("PASS stop loss: minimum distance respected for low/medium/high noise")


def run_performance_smoke() -> None:
    long_metrics = calculate_trade_plan_performance(
        direction="long",
        entry_price=100.0,
        initial_stop_loss=95.0,
        current_price=110.0,
        account_equity=10_000.0,
        risk_percent_per_trade=1.0,
        realized_r_multiple=1.5,
        highest_price=112.0,
        lowest_price=98.0,
    )
    assert_close(long_metrics["unrealized_r_multiple"], 2.0, "Long unrealized R-multiple should be correct")
    assert_close(long_metrics["realized_r_multiple"], 1.5, "Long realized R-multiple should stay as provided")
    assert_close(long_metrics["max_favorable_excursion"], 2.4, "Long MFE should be correct")
    assert_close(long_metrics["max_adverse_excursion"], 0.4, "Long MAE should be correct")
    assert_close(long_metrics["realized_pnl_amount"], 150.0, "Long realized PnL amount should be correct")
    assert_close(long_metrics["realized_pnl_percent"], 1.5, "Long realized PnL percent should be correct")
    assert_close(long_metrics["unrealized_pnl_amount"], 200.0, "Long unrealized PnL amount should be correct")
    assert_close(long_metrics["unrealized_pnl_percent"], 2.0, "Long unrealized PnL percent should be correct")
    assert_true(long_metrics["max_favorable_excursion"] >= 0.0, "Long MFE should stay >= 0.")
    assert_true(long_metrics["max_adverse_excursion"] >= 0.0, "Long MAE should stay >= 0.")
    print("PASS performance: long R-multiple, MFE, and MAE are correct")

    short_metrics = calculate_trade_plan_performance(
        direction="short",
        entry_price=100.0,
        initial_stop_loss=105.0,
        current_price=90.0,
        account_equity=10_000.0,
        risk_percent_per_trade=1.0,
        realized_r_multiple=1.25,
        highest_price=102.0,
        lowest_price=88.0,
    )
    assert_close(short_metrics["unrealized_r_multiple"], 2.0, "Short unrealized R-multiple should be correct")
    assert_close(short_metrics["realized_r_multiple"], 1.25, "Short realized R-multiple should stay as provided")
    assert_close(short_metrics["max_favorable_excursion"], 2.4, "Short MFE should be correct")
    assert_close(short_metrics["max_adverse_excursion"], 0.4, "Short MAE should be correct")
    assert_close(short_metrics["realized_pnl_amount"], 125.0, "Short realized PnL amount should be correct")
    assert_close(short_metrics["realized_pnl_percent"], 1.25, "Short realized PnL percent should be correct")
    assert_close(short_metrics["unrealized_pnl_amount"], 200.0, "Short unrealized PnL amount should be correct")
    assert_close(short_metrics["unrealized_pnl_percent"], 2.0, "Short unrealized PnL percent should be correct")
    assert_true(short_metrics["max_favorable_excursion"] >= 0.0, "Short MFE should stay >= 0.")
    assert_true(short_metrics["max_adverse_excursion"] >= 0.0, "Short MAE should stay >= 0.")
    print("PASS performance: short R-multiple, MFE, and MAE are correct")

    long_negative_excursion = calculate_trade_plan_performance(
        direction="long",
        entry_price=100.0,
        initial_stop_loss=95.0,
        current_price=99.0,
        account_equity=10_000.0,
        risk_percent_per_trade=1.0,
        highest_price=99.0,
        lowest_price=101.0,
    )
    short_negative_excursion = calculate_trade_plan_performance(
        direction="short",
        entry_price=100.0,
        initial_stop_loss=105.0,
        current_price=101.0,
        account_equity=10_000.0,
        risk_percent_per_trade=1.0,
        highest_price=99.0,
        lowest_price=101.0,
    )
    assert_true(long_negative_excursion["max_favorable_excursion"] >= 0.0, "Long MFE should be clamped at >= 0.")
    assert_true(long_negative_excursion["max_adverse_excursion"] >= 0.0, "Long MAE should be clamped at >= 0.")
    assert_true(short_negative_excursion["max_favorable_excursion"] >= 0.0, "Short MFE should be clamped at >= 0.")
    assert_true(short_negative_excursion["max_adverse_excursion"] >= 0.0, "Short MAE should be clamped at >= 0.")
    assert_rejected(
        lambda: calculate_trade_plan_performance(
            direction="long",
            entry_price=100.0,
            initial_stop_loss=95.0,
            current_price=110.0,
            account_equity=0.0,
            risk_percent_per_trade=1.0,
        ),
        "Performance should reject account_equity <= 0.",
    )
    assert_rejected(
        lambda: calculate_trade_plan_performance(
            direction="long",
            entry_price=100.0,
            initial_stop_loss=95.0,
            current_price=110.0,
            account_equity=10_000.0,
            risk_percent_per_trade=0.0,
        ),
        "Performance should reject risk_percent_per_trade <= 0.",
    )
    assert_rejected(
        lambda: calculate_trade_plan_performance(
            direction="long",
            entry_price=100.0,
            initial_stop_loss=95.0,
            current_price=110.0,
            account_equity=10_000.0,
            risk_percent_per_trade=2.01,
            market_type="futures",
            trading_style="scalping",
        ),
        "Performance should reject risk_percent_per_trade > 2 for futures/scalping.",
    )
    print("PASS performance: MFE/MAE remain non-negative in unfavorable paths")


def run_trade_management_event_smoke() -> None:
    previous_long = make_trade_plan("long", current_stop_loss=95.0, tp_hit_count=0)
    current_long = make_trade_plan("long", current_stop_loss=99.0, tp_hit_count=1, status="managed")
    long_events = detect_trade_management_events(previous_long, current_long, 106.0)
    long_event_types = [event["event_type"] for event in long_events]
    assert_true("tp1_hit" in long_event_types, "Long trade should emit tp1_hit after first target.")
    assert_true("sl_moved" in long_event_types, "Long trade should emit sl_moved after stop tightening.")
    long_message = format_trade_management_event_message(long_events[0], "fr")
    assert_true("BTC LONG" in long_message or "BTC LONG:" in long_message, "Formatted FR message should include symbol and direction.")

    previous_short = make_trade_plan("short", current_stop_loss=105.0, tp_hit_count=1)
    current_short = make_trade_plan("short", current_stop_loss=101.0, tp_hit_count=2, status="managed")
    short_events = detect_trade_management_events(previous_short, current_short, 89.0)
    short_event_types = [event["event_type"] for event in short_events]
    assert_true("tp2_hit" in short_event_types, "Short trade should emit tp2_hit after second target.")
    assert_true("sl_moved" in short_event_types, "Short trade should emit sl_moved after stop tightening.")
    assert_true("tpf_hit" not in short_event_types, "Short trade should not emit final target before TPF is reached.")

    stopped_plan = make_trade_plan("long", current_stop_loss=99.0, tp_hit_count=1, status="stopped")
    stopped_events = detect_trade_management_events(current_long, stopped_plan, 98.5)
    assert_true(any(event["event_type"] == "stopped" for event in stopped_events), "Stopped trade should emit stopped event.")

    invalidated_events = detect_trade_management_events(current_long, current_long, 102.0, invalidated=True)
    assert_true(any(event["event_type"] == "invalidated" for event in invalidated_events), "Invalidated trade should emit invalidated event.")
    print("PASS trade management: events and messages are generated correctly")

    simulated_jobs = simulate_trade_management(991001, previous_long, current_long, 106.0)
    assert_true(len(simulated_jobs) >= 1, "Trade simulation should enqueue at least one notification job.")
    queue_jobs = get_trade_management_jobs()
    assert_true(any(job["event_key"] == simulated_jobs[0]["event_key"] for job in queue_jobs), "Queued trade notification should be retrievable.")
    acknowledge_trade_management_event(991001, simulated_jobs[0]["event_key"])
    remaining_jobs = get_trade_management_jobs()
    assert_true(
        all(job["event_key"] != simulated_jobs[0]["event_key"] for job in remaining_jobs),
        "Acknowledging a trade notification should remove it from the queue.",
    )

    trade_id_user = 991002
    cleanup_db_trade_test_data(trade_id_user)
    simulated_jobs_with_trade_id = simulate_trade_management(
        trade_id_user,
        previous_long,
        current_long,
        106.0,
        trade_id="sim-trade-1",
    )
    persisted_trade_id_events = get_pending_trade_events(trade_id_user)
    assert_true(len(simulated_jobs_with_trade_id) >= 1, "Trade simulation with trade_id should still enqueue jobs.")
    assert_true(
        any(event["trade_id"] == "sim-trade-1" for event in persisted_trade_id_events),
        "Persisted trade events should keep the provided trade_id.",
    )
    for job in simulated_jobs_with_trade_id:
        acknowledge_trade_management_event(trade_id_user, job["event_key"])
    cleanup_db_trade_test_data(trade_id_user)
    print("PASS trade management: simulation queue and ack work correctly")


def make_trade_journal_entries() -> list[TradeJournalEntry]:
    return [
        make_trade_journal_entry(
            trade_id="t1",
            symbol="BTC",
            archetype="Trend continuation",
            exit_price=112.0,
            exit_reason="tp2",
            realized_r_multiple=2.4,
            tp_hit_count=2,
            feedback_label="good",
            closed_at="2026-04-26T02:00:00Z",
        ),
        make_trade_journal_entry(
            trade_id="t2",
            symbol="ETH",
            archetype=" Trend   continuation ",
            exit_price=99.0,
            exit_reason="stopped",
            realized_r_multiple=-0.2,
            tp_hit_count=1,
            stopped_after_tp=True,
            feedback_label="bad",
            created_at="2026-04-26T03:00:00Z",
            closed_at="2026-04-26T04:00:00Z",
        ),
        make_trade_journal_entry(
            trade_id="t3",
            symbol="SOL",
            direction="short",
            archetype="Fast momentum",
            market_type="futures",
            trading_style="scalping",
            initial_stop_loss=105.0,
            exit_price=92.5,
            exit_reason="tp1",
            realized_r_multiple=1.5,
            tp_hit_count=1,
            feedback_label="good",
            created_at="2026-04-26T05:00:00Z",
            closed_at="2026-04-26T05:30:00Z",
        ),
        make_trade_journal_entry(
            trade_id="t4",
            symbol="AVAX",
            archetype="Trend continuation",
            realized_r_multiple=0.0,
            exit_price=100.0,
            exit_reason="scratch",
            feedback_label="neutral",
            created_at="2026-04-26T06:00:00Z",
            closed_at="2026-04-26T06:20:00Z",
        ),
    ]


def run_trade_journal_stats_smoke() -> None:
    empty_stats = calculate_trade_journal_stats([])
    assert_true(empty_stats["total_trades"] == 0, "Empty journal should report zero trades.")

    open_trade = make_trade_journal_entry(
        trade_id="open-1",
        status="open",
        exit_price=None,
        exit_reason=None,
        closed_at=None,
    )
    assert_true(open_trade.status == "open", "Open trade journal entry should be allowed.")

    assert_rejected(
        lambda: make_trade_journal_entry(status="closed", exit_price=None),
        "Closed trade without exit_price should be rejected.",
    )
    assert_rejected(
        lambda: make_trade_journal_entry(created_at="2026-04-26T02:00:00Z", closed_at="2026-04-26T01:00:00Z"),
        "closed_at earlier than created_at should be rejected.",
    )

    entries = make_trade_journal_entries()
    stats = calculate_trade_journal_stats(entries)
    assert_true(stats["total_trades"] == 4, "Trade journal stats should count all trades.")
    assert_close(stats["win_rate"], 2 / 4, "Trade journal win rate should count only realized_r_multiple > 0.")
    assert_close(stats["average_r_multiple"], (2.4 - 0.2 + 1.5 + 0.0) / 4, "Average R multiple should be correct")
    assert_close(stats["average_tp_hit_count"], 5 / 4, "Average TP hit count should be correct")
    assert_close(stats["stopped_after_tp_rate"], 1 / 4, "Stopped-after-TP rate should stay measured over total trades.")
    assert_true("trend continuation" in stats["performance_by_archetype"], "Archetype stats should normalize the key.")
    assert_close(
        stats["performance_by_archetype"]["trend continuation"]["win_rate"],
        1 / 3,
        "Normalized trend continuation win rate should count 0R as non-win.",
    )
    print("PASS trade journal: aggregate stats are correct")


def run_adaptive_scoring_smoke() -> None:
    entries = make_trade_journal_entries()
    assert_rejected(
        lambda: adaptive_setup_score_adjustment(70.0, "Fast momentum", feedback_label="great"),
        "Invalid feedback_label should be rejected.",
    )

    boosted_score = adaptive_setup_score_adjustment(
        70.0,
        "Fast momentum",
        journal_entries=entries,
        feedback_label="good",
        noise_score=35.0,
    )
    penalized_score = adaptive_setup_score_adjustment(
        70.0,
        "Trend continuation",
        journal_entries=entries,
        feedback_label="bad",
        noise_score=78.0,
    )
    normalized_score = adaptive_setup_score_adjustment(
        70.0,
        "  Trend   continuation ",
        journal_entries=entries,
        feedback_label="neutral",
        noise_score=20.0,
    )
    canonical_score = adaptive_setup_score_adjustment(
        70.0,
        "trend continuation",
        journal_entries=entries,
        feedback_label="neutral",
        noise_score=20.0,
    )
    low_sample_entries = [
        make_trade_journal_entry(
            trade_id="small-1",
            archetype="Breakout Watch",
            realized_r_multiple=3.0,
            feedback_label="neutral",
        )
    ]
    low_sample_score = adaptive_setup_score_adjustment(
        70.0,
        " breakout   watch ",
        journal_entries=low_sample_entries,
        feedback_label="neutral",
        noise_score=20.0,
    )
    assert_true(boosted_score > 70.0, "Strong archetype performance should boost the setup score.")
    assert_true(penalized_score < 70.0, "Weak recent feedback + high noise should penalize the setup score.")
    assert_close(normalized_score, canonical_score, "Normalized archetype names should resolve to the same score")
    assert_true(abs(low_sample_score - 70.0) < 2.0, "Low sample archetype stats should not move score too much.")
    assert_true(0.0 <= boosted_score <= 100.0, "Adaptive scoring should stay bounded.")
    assert_true(0.0 <= penalized_score <= 100.0, "Adaptive scoring should stay bounded.")
    print("PASS adaptive scoring: boosts and penalties behave as expected")


def run_trade_db_smoke() -> None:
    user_id = 991099
    cleanup_db_trade_test_data(user_id)
    save_user(
        user_id,
        {
            "intro_seen": True,
            "language": "en",
            "level": "pro",
            "market": "spot",
            "trading_style": "intraday",
            "coins": ["BTC", "ETH", "SOL"],
            "alerts_enabled": True,
            "alerts_min_priority": "high",
        },
    )

    persisted_plan = save_trade_plan(user_id, make_trade_plan("long", status="managed"))
    loaded_plans = get_trade_plans_by_user(user_id)
    assert_true(len(loaded_plans) == 1, "TradePlan should persist and reload for the user.")
    assert_true(loaded_plans[0]["id"] == persisted_plan["id"], "Loaded TradePlan should match saved id.")

    updated_plan = update_trade_plan(
        persisted_plan["id"],
        {
            "current_stop_loss": 99.5,
            "tp_hit_count": 1,
            "status": "managed",
        },
    )
    assert_close(updated_plan["current_stop_loss"], 99.5, "Updated TradePlan stop loss should persist")
    reloaded_plans = get_trade_plans_by_user(user_id)
    assert_close(reloaded_plans[0]["current_stop_loss"], 99.5, "Reloaded TradePlan should include updated stop loss")
    print("PASS trade DB: save/load/update TradePlan")

    closed_journal_entry = make_trade_journal_entry(
        trade_id="journal-db-1",
        symbol="BTC",
        status="closed",
        closed_at="2026-04-26T03:00:00Z",
    )
    persisted_journal = save_trade_journal_entry(user_id, closed_journal_entry)
    loaded_journal = get_trade_journal_by_user(user_id)
    assert_true(len(loaded_journal) == 1, "TradeJournal should persist and reload for the user.")
    assert_true(loaded_journal[0]["trade_id"] == persisted_journal["trade_id"], "Loaded TradeJournal should match saved trade_id.")
    assert_rejected(
        lambda: save_trade_journal_entry(
            user_id,
            make_trade_journal_entry(
                trade_id="journal-open-invalid",
                status="open",
                exit_price=None,
                exit_reason=None,
                closed_at=None,
            ),
        ),
        "Open trade journal entries should not be persisted.",
    )
    print("PASS trade DB: save/load TradeJournal and closed-only persistence")

    persisted_event = save_trade_event(
        {
            "id": "event-db-1",
            "trade_id": persisted_plan["id"],
            "user_id": user_id,
            "event_type": "tp1_hit",
            "message": "TP1 simulated.",
            "created_at": "2026-04-26T03:30:00Z",
            "acknowledged": False,
        }
    )
    pending_events = get_pending_trade_events(user_id)
    assert_true(len(pending_events) == 1, "TradeEvent should persist as pending.")
    assert_true(pending_events[0]["id"] == persisted_event["id"], "Pending TradeEvent should match saved id.")
    acknowledge_trade_event(persisted_event["id"])
    pending_after_ack = get_pending_trade_events(user_id)
    assert_true(len(pending_after_ack) == 0, "Acknowledged TradeEvent should disappear from pending list.")
    print("PASS trade DB: save/load/ack TradeEvent")

    previous_long = make_trade_plan("long", current_stop_loss=95.0, tp_hit_count=0)
    current_long = make_trade_plan("long", current_stop_loss=99.0, tp_hit_count=1, status="managed")
    simulated_jobs = simulate_trade_management(user_id, previous_long, current_long, 106.0)
    merged_jobs = get_trade_management_jobs()
    matching_jobs = [job for job in merged_jobs if job["event_key"] in {item["event_key"] for item in simulated_jobs}]
    assert_true(
        len(matching_jobs) == len({item["event_key"] for item in simulated_jobs}),
        "Queue + DB should not duplicate the same trade management jobs.",
    )

    _TRADE_MANAGEMENT_JOB_QUEUE.clear()
    replay_jobs = get_trade_management_jobs()
    replay_keys = {job["event_key"] for job in replay_jobs}
    assert_true(
        all(item["event_key"] in replay_keys for item in simulated_jobs),
        "After clearing memory queue, pending trade events should replay from SQLite.",
    )

    for job in simulated_jobs:
        acknowledge_trade_management_event(user_id, job["event_key"])
    replay_after_ack = get_trade_management_jobs()
    assert_true(
        all(job["event_key"] not in {item["event_key"] for item in replay_after_ack} for job in simulated_jobs),
        "Ack should clear trade management jobs from both queue and SQLite replay.",
    )
    print("PASS trade DB: queue + DB replay and ack stay in sync")

    persisted_flow_plan = save_trade_plan(user_id, make_trade_plan("long", status="active"))
    previous_persisted_plan = make_trade_plan(
        "long",
        current_stop_loss=persisted_flow_plan["current_stop_loss"],
        tp_hit_count=persisted_flow_plan["tp_hit_count"],
        status=persisted_flow_plan["status"],
    )
    current_persisted_plan = make_trade_plan("long", current_stop_loss=99.0, tp_hit_count=1, status="managed")
    persisted_flow_jobs = simulate_trade_management(
        user_id,
        previous_persisted_plan,
        current_persisted_plan,
        106.0,
        trade_id=persisted_flow_plan["id"],
    )
    persisted_flow_events = get_pending_trade_events(user_id)
    assert_true(
        any(event["trade_id"] == persisted_flow_plan["id"] for event in persisted_flow_events),
        "Simulated persisted trade events should keep the saved trade_id.",
    )

    update_trade_plan(
        persisted_flow_plan["id"],
        {
            "current_stop_loss": current_persisted_plan.current_stop_loss,
            "tp_hit_count": current_persisted_plan.tp_hit_count,
            "status": current_persisted_plan.status,
        },
    )
    refreshed_plans = {plan["id"]: plan for plan in get_trade_plans_by_user(user_id)}
    refreshed_persisted_plan = refreshed_plans[persisted_flow_plan["id"]]
    assert_close(
        refreshed_persisted_plan["current_stop_loss"],
        current_persisted_plan.current_stop_loss,
        "Persisted trade plan should reflect simulated stop update.",
    )
    assert_true(
        refreshed_persisted_plan["tp_hit_count"] == current_persisted_plan.tp_hit_count,
        "Persisted trade plan should reflect simulated tp_hit_count update.",
    )
    assert_true(
        refreshed_persisted_plan["status"] == current_persisted_plan.status,
        "Persisted trade plan should reflect simulated status update.",
    )

    for job in persisted_flow_jobs:
        acknowledge_trade_management_event(user_id, job["event_key"])
    pending_after_persisted_flow_ack = get_pending_trade_events(user_id)
    assert_true(
        all(event["trade_id"] != persisted_flow_plan["id"] for event in pending_after_persisted_flow_ack),
        "Acknowledged persisted trade events should no longer remain pending.",
    )
    print("PASS trade DB: persisted TradePlan simulate flow works end-to-end")

    cleanup_db_trade_test_data(user_id)


def main() -> None:
    run_tradeplan_schema_smoke()
    run_stop_loss_smoke()
    run_performance_smoke()
    run_trade_management_event_smoke()
    run_trade_journal_stats_smoke()
    run_adaptive_scoring_smoke()
    run_trade_db_smoke()
    print("Smoke trade lifecycle checks completed successfully.")


if __name__ == "__main__":
    main()
