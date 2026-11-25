
"""Portfolio risk management -- concentration limits, clustering, drawdown breaker."""

import logging
import math

import yfinance as yf

from stockpulse.config.settings import load_strategies
from stockpulse.data.provider import (
    get_price_history,
    get_earnings_calendar_status,
)
from stockpulse.data.cache import get_cached, set_cached

logger = logging.getLogger(__name__)


def _get_ticker_info(ticker: str) -> dict:
    """Get sector and industry for a ticker via yfinance."""
    cache_key = f"ticker_info_{ticker}"
    cached = get_cached(cache_key)

    if cached is not None:
        return cached

    try:
        info = yf.Ticker(ticker).info

        result = {
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
        }

        set_cached(cache_key, result)
        return result

    except Exception:
        logger.exception("Failed to retrieve ticker information for %s", ticker)
        return {"sector": "Unknown", "industry": "Unknown"}


def _compute_correlation(
    ticker_a: str,
    ticker_b: str,
    period: int = 60,
) -> float:
    """Compute daily return correlation between two tickers over N days."""
    cache_key = (
        f"corr_{min(ticker_a, ticker_b)}_"
        f"{max(ticker_a, ticker_b)}_{period}"
    )

    cached = get_cached(cache_key)

    if cached is not None:
        return cached

    try:
        df_a = get_price_history(ticker_a, period="6mo")
        df_b = get_price_history(ticker_b, period="6mo")

        if df_a.empty or df_b.empty or "Close" not in df_a.columns or "Close" not in df_b.columns:
            return 0.0

        ret_a = df_a["Close"].pct_change().dropna().tail(period)
        ret_b = df_b["Close"].pct_change().dropna().tail(period)

        common = ret_a.index.intersection(ret_b.index)

        if len(common) < 20:
            return 0.0

        correlation = float(
            ret_a.loc[common].corr(ret_b.loc[common])
        )

        if math.isnan(correlation):
            correlation = 0.0

        set_cached(cache_key, correlation)
        return correlation

    except Exception:
        logger.exception(
            "Failed to calculate correlation for %s and %s",
            ticker_a,
            ticker_b,
        )
        return 0.0


def get_position_clusters(tickers: list[str]) -> dict[str, list[str]]:
    """Group tickers into clusters based on sub-industry and correlation.

    Two tickers are in the same cluster if:
    - They have the same GICS sub-industry, or
    - Their 60-day daily return correlation is at least 0.75.

    Returns {cluster_id: [tickers]}.
    """
    if not tickers:
        return {}

    info = {ticker: _get_ticker_info(ticker) for ticker in tickers}

    clusters = {}
    cluster_id = 0
    assigned = {}

    for i, ticker_a in enumerate(tickers):
        if ticker_a in assigned:
            continue

        cluster = [ticker_a]
        assigned[ticker_a] = cluster_id

        for ticker_b in tickers[i + 1:]:
            if ticker_b in assigned:
                continue

            same_industry = (
                info[ticker_a]["industry"] == info[ticker_b]["industry"]
                and info[ticker_a]["industry"] != "Unknown"
            )

            high_correlation = False

            if not same_industry:
                correlation = _compute_correlation(ticker_a, ticker_b)
                high_correlation = correlation >= 0.75

            if same_industry or high_correlation:
                cluster.append(ticker_b)
                assigned[ticker_b] = cluster_id

        clusters[f"cluster_{cluster_id}"] = cluster
        cluster_id += 1

    return clusters


def check_concentration_limits(
    candidate_ticker: str,
    current_positions: list[dict],
    portfolio_value: float,
) -> dict:
    """Check concentration, clustering, and earnings risks.

    Earnings calendar status:
    - clear: provider lookup succeeded and no blackout was found.
    - blackout: an earnings date falls inside the configured blackout period.
    - unknown: earnings information could not be verified.

    Unknown earnings status blocks risk clearance. This is intentionally
    fail-closed: unavailable risk data must not be treated as safe.

    Returns:
        allowed: Whether risk checks permit the candidate.
        reasons: Reasons for blocking the candidate.
        size_multiplier: Position-size adjustment for correlated holdings.
        sector: Candidate sector.
        industry: Candidate industry.
        cluster_tickers: Existing correlated or same-industry holdings.
        earnings_status: clear, blackout, or unknown.
    """
    risk_cfg = load_strategies().get("risk", {})

    max_positions = risk_cfg.get("max_positions", 8)
    max_position_pct = risk_cfg.get("max_position_pct", 8)
    max_sector_pct = risk_cfg.get("max_sector_pct", 25)
    blackout_days = risk_cfg.get("earnings_blackout_days", 3)

    reasons = []
    size_multiplier = 1.0

    # Maximum position count.
    if len(current_positions) >= max_positions:
        reasons.append(f"Max positions ({max_positions}) reached")

    # Candidate classification.
    candidate_info = _get_ticker_info(candidate_ticker)
    candidate_sector = candidate_info["sector"]
    candidate_industry = candidate_info["industry"]

    sector_exposure = 0.0
    industry_exposure = 0.0
    cluster_tickers = []

    # Calculate existing sector and industry exposure.
    for position in current_positions:
        position_info = _get_ticker_info(position["ticker"])

        position_price = position.get(
            "current_price",
            position["entry_price"],
        )
        position_value = position["shares"] * position_price

        position_pct = (
            position_value / portfolio_value * 100
            if portfolio_value > 0
            else 0.0
        )

        if position_info["sector"] == candidate_sector:
            sector_exposure += position_pct

        if (
            position_info["industry"] == candidate_industry
            and candidate_industry != "Unknown"
        ):
            industry_exposure += position_pct
            cluster_tickers.append(position["ticker"])

    # Check correlation-based clustering.
    for position in current_positions:
        ticker = position["ticker"]

        if ticker in cluster_tickers:
            continue

        correlation = _compute_correlation(candidate_ticker, ticker)

        if correlation >= 0.75:
            cluster_tickers.append(ticker)

    # Sector concentration cap.
    if sector_exposure + max_position_pct > max_sector_pct:
        reasons.append(
            f"Sector '{candidate_sector}' at {sector_exposure:.1f}%, "
            f"adding {max_position_pct}% would exceed "
            f"{max_sector_pct}% cap"
        )

    # Sub-industry concentration cap.
    if industry_exposure + max_position_pct > 15:
        reasons.append(
            f"Industry '{candidate_industry}' at "
            f"{industry_exposure:.1f}%, adding would exceed "
            f"15% sub-industry cap"
        )

    # Reduce suggested position size for clustered holdings.
    if cluster_tickers:
        size_multiplier = 0.6

    # Earnings blackout and data availability.
    earnings_status = "unknown"

    try:
        calendar = get_earnings_calendar_status(candidate_ticker)

        if calendar.get("available") is not True:
            reasons.append(
                f"Earnings calendar unavailable for {candidate_ticker}; "
                "earnings risk could not be verified"
            )

        else:
            earnings_status = "clear"

            for earnings in calendar.get("dates", []):
                days_away = earnings.get("days_away", 999)

                if 0 <= days_away <= blackout_days:
                    earnings_status = "blackout"

                    reasons.append(
                        f"Earnings blackout: {candidate_ticker} "
                        f"reports in {days_away} days"
                    )
                    break

    except Exception as exc:
        logger.exception(
            "Earnings risk assessment failed for %s",
            candidate_ticker,
        )

        reasons.append(
            f"Earnings risk assessment failed for {candidate_ticker}: "
            f"{type(exc).__name__}"
        )

    return {
        "allowed": len(reasons) == 0,
        "reasons": reasons,
        "size_multiplier": size_multiplier,
        "sector": candidate_sector,
        "industry": candidate_industry,
        "cluster_tickers": cluster_tickers,
        "earnings_status": earnings_status,
    }


def compute_position_size(
    portfolio_value: float,
    entry_price: float,
    atr: float,
    confidence: int = 50,
) -> dict:
    """Compute volatility-adjusted position size.

    Base risk per trade = 0.75% of portfolio.
    Confidence scales from 0.75x to 1.25x.
    Stop distance uses 1.5 ATR.

    Returns shares, dollar_amount, risk_dollars, stop_price,
    and confidence_multiplier.
    """
    risk_cfg = load_strategies().get("risk", {})

    risk_pct = risk_cfg.get("risk_per_trade_pct", 0.75)
    max_position_pct = risk_cfg.get("max_position_pct", 8)

    risk_dollars = portfolio_value * (risk_pct / 100)

    confidence = max(0, min(confidence, 100))
    confidence_multiplier = 0.75 + (confidence / 100) * 0.50

    stop_distance = (
        1.5 * atr
        if atr > 0
        else entry_price * 0.03
    )

    shares_from_risk = (
        int(
            (risk_dollars * confidence_multiplier) / stop_distance
        )
        if stop_distance > 0
        else 0
    )

    max_dollars = portfolio_value * (max_position_pct / 100)

    max_shares = (
        int(max_dollars / entry_price)
        if entry_price > 0
        else 0
    )

    shares = min(shares_from_risk, max_shares)
    shares = max(shares, 0)

    return {
        "shares": shares,
        "dollar_amount": round(shares * entry_price, 2),
        "risk_dollars": round(
            risk_dollars * confidence_multiplier,
            2,
        ),
        "stop_price": round(entry_price - stop_distance, 2),
        "confidence_multiplier": round(
            confidence_multiplier,
            2,
        ),
    }


def check_drawdown_status(
    current_equity: float,
    peak_equity: float,
) -> dict:
    """Check portfolio drawdown and return trading restrictions.

    Rules:
    - At -8%: cut new position sizes in half.
    - At -12%: pause all new buys.
    """
    risk_cfg = load_strategies().get("risk", {})

    half_threshold = risk_cfg.get("drawdown_half", 8)
    pause_threshold = risk_cfg.get("drawdown_pause", 12)

    if peak_equity <= 0:
        return {
            "drawdown_pct": 0,
            "size_multiplier": 1.0,
            "new_buys_paused": False,
        }

    drawdown_pct = (
        (peak_equity - current_equity) / peak_equity
    ) * 100

    size_multiplier = 1.0
    new_buys_paused = False

    if drawdown_pct >= pause_threshold:
        new_buys_paused = True
        size_multiplier = 0.0

    elif drawdown_pct >= half_threshold:
        size_multiplier = 0.5

    return {
        "drawdown_pct": round(drawdown_pct, 2),
        "size_multiplier": size_multiplier,
        "new_buys_paused": new_buys_paused,
    }
