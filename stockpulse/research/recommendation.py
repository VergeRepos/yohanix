
"""Buy/sell/hold recommendation engine."""
import logging
from datetime import datetime

import pandas as pd

from stockpulse.config.settings import load_portfolio, load_strategies
from stockpulse.signals.engine import (
    compute_all_signals,
    check_confirmation_buckets,
    compute_score_acceleration,
)
from stockpulse.signals.composite import (
    compute_composite_score,
    classify_action,
    compute_confidence,
)
from stockpulse.signals.pead import calc_pead_score
from stockpulse.research.scoring import compute_invalidation

logger = logging.getLogger(__name__)


def _build_technical_summary(signals: dict) -> str:
    parts = []

    rsi = signals.get("rsi", {})
    if rsi.get("value") is not None:
        parts.append(f"RSI: {rsi['value']:.0f}")

    macd = signals.get("macd", {})
    if macd.get("score", 0) > 20:
        parts.append("MACD: bullish")
    elif macd.get("score", 0) < -20:
        parts.append("MACD: bearish")
    else:
        parts.append("MACD: neutral")

    ma = signals.get("moving_averages", {})
    if ma.get("score", 0) > 0:
        parts.append("Above key SMAs")
    elif ma.get("score", 0) < 0:
        parts.append("Below key SMAs")

    vol = signals.get("volume", {})
    if abs(vol.get("score", 0)) > 30:
        parts.append("Volume spike detected")

    adx = signals.get("adx", {})
    if adx.get("score", 0) > 20:
        parts.append("Strong uptrend (ADX)")
    elif adx.get("score", 0) < -20:
        parts.append("Strong downtrend (ADX)")

    return ". ".join(parts) if parts else "Insufficient technical data"


def _build_catalyst_summary(signals: dict) -> str:
    parts = []

    if signals.get("earnings", {}).get("score", 0) > 0:
        parts.append("Earnings approaching")

    if signals.get("sec_filing", {}).get("score", 0) > 10:
        parts.append("Recent SEC filing activity")

    news = signals.get("news_sentiment", {})
    if news.get("score", 0) > 10:
        parts.append("Positive news sentiment")
    elif news.get("score", 0) < -10:
        parts.append("Negative news sentiment")

    return ". ".join(parts) if parts else "No significant catalysts detected"


def _build_thesis(action: str, signals: dict, composite: float) -> str:
    direction = "Bullish" if composite > 0 else "Bearish"

    def weighted(name, data):
        return data.get("score", 0) * data.get("weight", 0)

    supporting = [
        (name, data)
        for name, data in signals.items()
        if data.get("weight", 0) > 0
        and (
            (composite > 0 and data.get("score", 0) > 0)
            or (composite < 0 and data.get("score", 0) < 0)
        )
    ]

    opposing = [
        (name, data)
        for name, data in signals.items()
        if data.get("weight", 0) > 0
        and (
            (composite > 0 and data.get("score", 0) < -10)
            or (composite < 0 and data.get("score", 0) > 10)
        )
    ]

    if supporting:
        best = max(
            supporting,
            key=lambda item: abs(weighted(item[0], item[1])),
        )
        parts = [
            f"{direction} ({composite:.1f}) driven by "
            f"{best[0]} ({best[1]['score']:+.0f})"
        ]
    else:
        parts = [
            f"Weakly {direction.lower()} ({composite:.1f}), "
            "no strong supporting signals"
        ]

    if opposing:
        worst = max(
            opposing,
            key=lambda item: abs(weighted(item[0], item[1])),
        )
        parts.append(
            f"Headwind: {worst[0]} ({worst[1]['score']:+.0f})"
        )

    return ". ".join(parts)


def _not_assessed_risk() -> dict:
    """Return an explicit risk status for non-BUY recommendations."""
    return {
        "allowed": None,
        "reasons": ["Risk assessment not run: recommendation is not BUY"],
        "size_multiplier": 1.0,
        "sector": "",
        "industry": "",
        "cluster_tickers": [],
        "earnings_status": "not_assessed",
    }


def _failed_risk_assessment(exc: Exception) -> dict:
    """Fail closed when a BUY candidate cannot be risk-assessed."""
    return {
        "allowed": False,
        "reasons": [
            f"Risk assessment unavailable: {type(exc).__name__}"
        ],
        "size_multiplier": 0.0,
        "sector": "",
        "industry": "",
        "cluster_tickers": [],
        "earnings_status": "unknown",
    }


def _assess_buy_risk(ticker: str) -> dict:
    """Run the risk gate only for BUY candidates."""
    try:
        from stockpulse.portfolio.risk import check_concentration_limits

        portfolio = load_portfolio()
        if not isinstance(portfolio, dict):
            raise ValueError("Portfolio configuration is invalid")

        positions = portfolio.get("positions", [])
        if not isinstance(positions, list):
            raise ValueError("Portfolio positions must be a list")

        total_value = sum(
            float(position.get("shares", 0))
            * float(
                position.get(
                    "current_price",
                    position.get("entry_price", 0),
                )
            )
            for position in positions
        )

        risk_check = check_concentration_limits(
            ticker,
            positions,
            total_value,
        )

        if not isinstance(risk_check, dict):
            raise ValueError("Risk assessment returned an invalid result")

        risk_check = dict(risk_check)
        risk_check.setdefault("reasons", [])
        risk_check.setdefault("size_multiplier", 1.0)
        risk_check.setdefault("sector", "")
        risk_check.setdefault("industry", "")
        risk_check.setdefault("cluster_tickers", [])
        risk_check.setdefault("earnings_status", "unknown")

        # A missing or unverified earnings calendar must never pass.
        if (
            risk_check.get("allowed") is True
            and risk_check.get("earnings_status") != "clear"
        ):
            risk_check["allowed"] = False
            risk_check["size_multiplier"] = 0.0
            risk_check["reasons"] = list(risk_check["reasons"])
            risk_check["reasons"].append(
                "Risk gate blocked: earnings calendar is not verified clear"
            )

        return risk_check

    except Exception as exc:
        logger.exception("Risk assessment failed for %s", ticker)
        return _failed_risk_assessment(exc)


def generate_recommendation(
    ticker: str,
    df: pd.DataFrame,
    use_llm: bool = True,
) -> dict:
    signals = compute_all_signals(ticker, df, use_llm=use_llm)
    composite = compute_composite_score(signals)
    action = classify_action(composite)
    confidence = compute_confidence(composite)
    invalidation = compute_invalidation(ticker, action, df)

    confirmation = check_confirmation_buckets(signals)

    # BUY confirmation requires Trend + (Participation or Catalyst).
    buckets = confirmation.get("buckets", {})
    trend_confirms = buckets.get("trend", {}).get("confirms", False)
    participation_confirms = buckets.get("participation", {}).get(
        "confirms", False
    )
    catalyst_confirms = buckets.get("catalyst", {}).get("confirms", False)

    if action == "BUY":
        if not trend_confirms:
            action = "WATCHLIST"
        elif not (participation_confirms or catalyst_confirms):
            action = "WATCHLIST"

    # Score acceleration modifier.
    accel_bonus = compute_score_acceleration(
        ticker,
        composite,
        confirmation,
    )
    composite += accel_bonus

    # Post-earnings announcement drift overlay.
    pead_score = calc_pead_score(ticker)
    if abs(pead_score) > 5:
        pead_weight = 0.05 if abs(pead_score) >= 30 else 0.0
        signals["pead"] = {
            "score": pead_score,
            "weight": pead_weight,
            "value": pead_score,
        }
        composite += pead_score * max(pead_weight, 0.03)

    # Sector rotation overlay.
    try:
        from stockpulse.signals.relative_strength import (
            compute_sector_rotation_bonus,
        )

        sector = ""
        risk_data = signals.get("relative_strength", {})
        if hasattr(risk_data, "get"):
            sector = risk_data.get("sector", "")

        sector_bonus = compute_sector_rotation_bonus(ticker, sector)
        if sector_bonus != 0:
            composite += sector_bonus
            signals["sector_rotation"] = {
                "score": sector_bonus,
                "weight": 0.0,
                "value": sector_bonus,
            }
    except Exception:
        logger.debug(
            "Sector rotation overlay unavailable for %s",
            ticker,
            exc_info=True,
        )

    # Re-classify after score overlays.
    action = classify_action(composite)
    confidence = compute_confidence(composite)

    # Re-apply confirmation requirements.
    if action == "BUY" and not confirmation.get("passes", False):
        action = "WATCHLIST"

    # Relaxed WATCHLIST threshold.
    if action == "HOLD":
        relaxed_threshold = (
            load_strategies()
            .get("thresholds", {})
            .get("watchlist_relaxed", 30)
        )

        if composite >= relaxed_threshold:
            trend_confirms = (
                confirmation.get("buckets", {})
                .get("trend", {})
                .get("confirms", False)
            )
            rs_score = signals.get("relative_strength", {}).get(
                "score", 0
            )
            breakout_score = signals.get("breakout", {}).get(
                "score", 0
            )
            participation_confirms = (
                confirmation.get("buckets", {})
                .get("participation", {})
                .get("confirms", False)
            )

            if trend_confirms and (
                rs_score >= 60
                or breakout_score >= 15
                or participation_confirms
            ):
                action = "WATCHLIST"

    # WATCHLIST -> BUY upgrade.
    if action == "WATCHLIST" and composite >= 50:
        vol_score = signals.get("volume", {}).get("score", 0)
        breakout_score = signals.get("breakout", {}).get("score", 0)

        # Fast-track: score >= 70 and strong volume confirmation.
        if composite >= 70 and vol_score >= 60:
            action = "BUY"
        elif vol_score >= 30 or breakout_score >= 20:
            if confirmation.get("passes", False):
                action = "BUY"

    # Calculate the technical high-conviction flag.
    high_conviction = False

    if action == "BUY" and composite >= 70:
        if confirmation.get("confirming_count", 0) >= 3:
            participation = (
                confirmation.get("buckets", {})
                .get("participation", {})
                .get("confirms", False)
            )
            pead = signals.get("pead", {}).get("score", 0)
            breakout_score = signals.get("breakout", {}).get(
                "score", 0
            )

            if participation or abs(pead) > 10 or breakout_score > 20:
                high_conviction = True

    # Position caution overlay.
    position_caution = False
    try:
        portfolio = load_portfolio()
        held_tickers = [
            position["ticker"]
            for position in portfolio.get("positions", [])
        ]

        if ticker in held_tickers and composite < 10:
            position_caution = True
    except Exception:
        logger.debug(
            "Could not evaluate position caution for %s",
            ticker,
            exc_info=True,
        )

    # Run risk assessment only for BUY candidates.
    if action == "BUY":
        risk_check = _assess_buy_risk(ticker)

        # High conviction requires a passing risk gate and a verified
        # clear earnings calendar.
        high_conviction = (
            high_conviction
            and risk_check.get("allowed") is True
            and risk_check.get("earnings_status") == "clear"
        )
    else:
        risk_check = _not_assessed_risk()

    return {
        "ticker": ticker,
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "confidence": confidence,
        "composite_score": round(composite, 2),
        "thesis": _build_thesis(action, signals, composite),
        "technical_summary": _build_technical_summary(signals),
        "catalyst_summary": _build_catalyst_summary(signals),
        "invalidation": invalidation,
        "signals": signals,
        "confirmation": confirmation,
        "risk": risk_check,
        "high_conviction": high_conviction,
        "position_caution": position_caution,
    }


def rank_recommendations(
    recommendations: list[dict],
) -> list[dict]:
    return sorted(
        recommendations,
        key=lambda recommendation: abs(
            recommendation["composite_score"]
        ),
        reverse=True,
    )
