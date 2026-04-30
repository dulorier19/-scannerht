#!/usr/bin/env python3
from __future__ import annotations

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

from backend.services import (  # noqa: E402
    get_alerts_overview,
    get_scanner_overview,
    get_signals_overview,
    reset_user,
    save_user,
    _build_signals_overview_from_market,
)


WATCHLIST = ["BTC", "ETH", "SOL"]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def setup_user(
    user_id: int,
    *,
    level: str,
    market: str = "spot",
    trading_style: str = "intraday",
    scanner_limit: int | None = None,
) -> None:
    reset_user(user_id, keep_intro_seen=False)
    patch = {
        "intro_seen": True,
        "language": "en",
        "level": level,
        "market": market,
        "trading_style": trading_style,
        "coins": WATCHLIST,
        "alerts_enabled": True,
    }
    if scanner_limit is not None:
        patch["scanner_limit"] = scanner_limit
    save_user(user_id, patch)


def make_market_overview(
    *,
    market_type: str,
    trading_style: str,
    regime: str,
    volatility_label: str,
    assets: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "market_type": market_type,
        "trading_style": trading_style,
        "regime": regime,
        "sentiment_score": 60,
        "volatility_label": volatility_label,
        "focus_window": "Test window",
        "outlook_headline": "Smoke test overview",
        "checklist": [],
        "assets": assets,
        "data_mode": "modelled",
        "data_provider": None,
        "data_updated_at": None,
        "data_cached": False,
        "data_stale": False,
    }


def status_rank(status: str) -> int:
    return {
        "Active": 2,
        "Watch": 1,
        "Stand aside": 0,
    }.get(status, -1)


def run_level_smoke() -> None:
    beginner_id = 991001
    medium_id = 991002
    pro_id = 991003

    setup_user(beginner_id, level="beginner")
    setup_user(medium_id, level="medium")
    setup_user(pro_id, level="pro", scanner_limit=7)

    beginner_signals = get_signals_overview(beginner_id)
    beginner_alerts = get_alerts_overview(beginner_id)
    beginner_scanner = get_scanner_overview(beginner_id)
    assert_true(len(beginner_signals["setups"]) == 1, "Beginner should expose exactly 1 signal setup.")
    assert_true(beginner_alerts["delivery_min_priority"] == "High", "Beginner alerts minimum priority should be High.")
    assert_true(beginner_scanner["visible_count"] == 3, "Beginner scanner visible_count should be 3.")
    print("PASS beginner: signals=1, alerts=High, scanner=3")

    medium_signals = get_signals_overview(medium_id)
    medium_alerts = get_alerts_overview(medium_id)
    medium_scanner = get_scanner_overview(medium_id)
    assert_true(len(medium_signals["setups"]) > 1, "Medium should expose more than 1 signal setup.")
    assert_true(medium_alerts["delivery_min_priority"] == "Medium", "Medium alerts minimum priority should be Medium.")
    assert_true(medium_scanner["visible_count"] == 5, "Medium scanner visible_count should be 5.")
    print("PASS medium: signals>1, alerts=Medium, scanner=5")

    pro_scanner = get_scanner_overview(pro_id)
    assert_true(pro_scanner["visible_count"] == min(7, pro_scanner["universe_size"]), "Pro scanner limit should be respected.")
    print(f"PASS pro: scanner visible_count={pro_scanner['visible_count']} with configured limit=7")


def run_market_style_smoke() -> None:
    borderline_assets = [
        {
            "symbol": "BTC",
            "pulse_score": 72,
            "breakout_score": 68,
            "volatility_score": 58,
            "bias": "Long bias",
            "setup": "Trend continuation",
            "signal": "Ready",
            "last_price": 70000.0,
            "price_change_percent": 0.9,
            "quote_volume": 1000000.0,
        },
        {
            "symbol": "ETH",
            "pulse_score": 64,
            "breakout_score": 60,
            "volatility_score": 61,
            "bias": "Watch for reclaim",
            "setup": "Breakout watch",
            "signal": "Watch",
            "last_price": 3500.0,
            "price_change_percent": 0.4,
            "quote_volume": 750000.0,
        },
        {
            "symbol": "SOL",
            "pulse_score": 59,
            "breakout_score": 58,
            "volatility_score": 65,
            "bias": "Watch for reclaim",
            "setup": "Breakout watch",
            "signal": "Watch",
            "last_price": 180.0,
            "price_change_percent": 0.2,
            "quote_volume": 500000.0,
        },
    ]

    spot_intraday = _build_signals_overview_from_market(
        make_market_overview(
            market_type="spot",
            trading_style="intraday",
            regime="Selective continuation",
            volatility_label="Active",
            assets=borderline_assets,
        ),
        "pro",
    )
    futures_scalping = _build_signals_overview_from_market(
        make_market_overview(
            market_type="futures",
            trading_style="scalping",
            regime="Selective continuation",
            volatility_label="Active",
            assets=borderline_assets,
        ),
        "pro",
    )

    avg_spot = sum(setup["setup_quality"] for setup in spot_intraday["setups"]) / len(spot_intraday["setups"])
    avg_futures = sum(setup["setup_quality"] for setup in futures_scalping["setups"]) / len(futures_scalping["setups"])
    assert_true(
        futures_scalping["ready_count"] <= spot_intraday["ready_count"] or avg_futures <= avg_spot,
        "futures/scalping should be stricter than spot/intraday.",
    )
    print(
        "PASS market/style strictness:",
        f"spot ready={spot_intraday['ready_count']} avg_quality={avg_spot:.1f}",
        f"| futures ready={futures_scalping['ready_count']} avg_quality={avg_futures:.1f}",
    )


def run_regime_smoke() -> None:
    weak_asset = [
        {
            "symbol": "BTC",
            "pulse_score": 58,
            "breakout_score": 56,
            "volatility_score": 70,
            "bias": "Watch for reclaim",
            "setup": "Breakout watch",
            "signal": "Watch",
            "last_price": 70000.0,
            "price_change_percent": 0.0,
            "quote_volume": 900000.0,
        }
    ]

    calm = _build_signals_overview_from_market(
        make_market_overview(
            market_type="spot",
            trading_style="intraday",
            regime="Risk-on continuation",
            volatility_label="Compressed",
            assets=weak_asset,
        ),
        "pro",
    )
    harsh = _build_signals_overview_from_market(
        make_market_overview(
            market_type="spot",
            trading_style="intraday",
            regime="Defensive chop",
            volatility_label="Explosive",
            assets=weak_asset,
        ),
        "pro",
    )

    calm_status = calm["setups"][0]["status"]
    harsh_status = harsh["setups"][0]["status"]
    assert_true(
        status_rank(harsh_status) < status_rank(calm_status),
        "Defensive/Explosive conditions should downgrade weaker setups.",
    )
    print(f"PASS regime downgrade: calm={calm_status} -> harsh={harsh_status}")


def main() -> None:
    run_level_smoke()
    run_market_style_smoke()
    run_regime_smoke()
    print("Smoke engine checks completed successfully.")


if __name__ == "__main__":
    main()
