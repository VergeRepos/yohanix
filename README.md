<div align="center">
  <img src="stockpulse-ui/public/favicon.svg" alt="Yohanix" width="80" />
  <h1>Yohanix</h1>
  <p><strong>Professional Financial Research and Market Intelligence Platform</strong></p>
  <p>
    <img src="https://img.shields.io/badge/python-3.13-blue?style=flat-square" alt="Python 3.13" />
    <img src="https://img.shields.io/badge/next.js-16-black?style=flat-square" alt="Next.js 16" />
    <img src="https://img.shields.io/badge/tests-337%20passing-brightgreen?style=flat-square" alt="Tests" />
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License" />
  </p>
  <p>Scans the S&P 500, generates buy/sell/hold recommendations with composite confidence scores, runs an always-on portfolio advisor, sends Telegram and Discord alerts, and includes a professional Dark Glass web dashboard.</p>
  <p><strong>Zero subscriptions. Free data only. Self-hosted. Never auto-trades.</strong></p>
</div>

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start & Installation](#quick-start--installation)
- [Running Yohanix](#running-yohanix)
- [Signal Engine](#signal-engine)
- [Portfolio Advisor](#portfolio-advisor)
- [Alerts (Telegram & Discord)](#alerts-telegram--discord)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Testing](#testing)
- [License](#license)

---

## Features

### Scanning and Signals
- Daily S&P 500 scanning with 11 calibrated signals and a composite scoring engine
- 5-tier classification: **BUY** / **WATCHLIST** / **HOLD** / **CAUTION** / **SELL**
- 3-bucket confirmation system: signals must agree across Trend, Participation, and Catalyst
- Score acceleration bonus for improving tickers (capped at +5 points)
- Sector rotation overlay (+/- 4 points based on sector momentum)
- Post-earnings drift (PEAD) overlay with 5% weight on confirmed surprise + tape follow-through
- Auto-discovery of new opportunities; stale tickers removed after 5 days

### Portfolio Advisor (Always-On, Never Auto-Trades)
- Event-driven suggestions with 3 severity levels: Urgent, Actionable, Informational
- Progressive position sizing ladder (starter 3% -> add1 5% -> add2 7% -> full 12% on BUY)
- Market regime-aware cash reserves and threshold adjustments
- Tax lot tracking with FIFO sell selection, short/long-term classification, wash sale detection
- Swap suggestions with strict guardrails (min score gap, persistence, cluster separation)

### Risk Management
- Sector caps (25%), position limits (8%), correlation clustering
- Drawdown breakers: -8% half size, -12% pause new buys
- Earnings blackout (3-day no-entry window)
- ATR-based position sizing and stop levels

### Web Dashboard
- Dark Glass themed Next.js 16 UI with 9 pages
- Wealthsimple portfolio import (paste account text)
- Manual position add/edit/delete with "I Did This" execution feedback
- TradingView chart integration with signal overlay

---

## Architecture

```
yohanix (systemd)          yohanix-api (port 18000)     yohanix-ui (port 3003)
    |                              |                              |
    |-- 09:35 Morning scan    <-- REST API (FastAPI) -->     Dark Glass UI
    |-- 30min Intraday check       |                         9 pages
    |-- 16:30 EOD recap            |-- /api/dashboard        TradingView charts
    |-- 2h SEC filing scan         |-- /api/watchlist        Signal breakdown
    |-- 30min Portfolio check      |-- /api/portfolio        Report viewer
    |-- Signal tracking            |-- /api/signals          Advisor panel
    |-- Sun Weekly digest          |-- /api/advisor          Allocation advisor
    |                              |-- /api/allocate         Settings editor
    v                              |-- /api/validation       Portfolio import
  Telegram / Discord               |-- /api/reports
  alerts.log                       |-- /api/config
                                   v
                              outputs/reports/
                              outputs/json/
```

---

## Quick Start & Installation

### Prerequisites
- Python 3.12+ (3.13 recommended)
- Node.js 18+ (for the web dashboard)
- A free [Finnhub](https://finnhub.io) API key

### Installation (Windows & Linux / macOS)

Clone the repository and run setup:

```bash
git clone https://github.com/NightBaRron1412/yohanix.git
cd yohanix

make setup                    # Creates venv, installs dependencies, initializes config
```

1. Get a free API key at [Finnhub](https://finnhub.io).
2. Edit `.env` and set `FINNHUB_API_KEY=your_api_key`.
3. Validate your setup:
   ```bash
   make check
   ```

---

## Running Yohanix

### 1. Run a One-Shot S&P 500 Scan
```bash
make run
```

### 2. Start the Web Dashboard & API Server
```bash
make api                      # Starts FastAPI backend on port 18000
```
In a separate terminal, start the Next.js frontend:
```bash
cd stockpulse-ui && npm install && npm run dev
```
*(Or use `make ui` if supported)*

### 3. Start Background Scheduler (Automated Scans & Alerts)
```bash
make start
```

---

## Signal Engine

Yohanix computes 11 technical, fundamental, and catalyst signals, combines them into a weighted composite score in `[-100, +100]`, and classifies them into action tiers:

| Signal | Weight | Description |
|--------|--------|-------------|
| **SEC Filing** | 18% | 8-K, 10-K/10-Q filings + Form 4 insider purchases |
| **Breakout** | 15% | Multi-period breakout with volume confirmation (RVOL >= 1.5) |
| **Volume** | 14% | Relative volume (RVOL) participation confirm |
| **Relative Strength** | 11% | Excess return vs SPY benchmark + sector ETF |
| **Moving Averages** | 10% | 20 EMA / 50 SMA / 200 SMA stack |
| **News Sentiment** | 8% | Sentiment analysis with keyword fallback |
| **RSI** | 7% | 14-period RSI with uptrend/downtrend zones |
| **MACD** | 7% | Crossover and histogram momentum |
| **ADX** | 6% | Trend strength indicator |
| **PEAD** | 5% | Post-earnings announcement drift |
| **Gap** | 4% | ATR-normalized gap detection |

### Classification Thresholds
- **BUY**: `>= 55` (with bucket confirmation & verified clear earnings)
- **WATCHLIST**: `>= 32` (relaxed at `25` with strong trend/RS)
- **HOLD**: Between WATCHLIST and CAUTION
- **CAUTION**: `<= -30`
- **SELL**: `<= -65`

---

## Alerts (Telegram & Discord)

Configure your `.env` file to receive real-time research alerts:

```env
ALERTS_TELEGRAM=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

ALERTS_DISCORD=true
DISCORD_WEBHOOK_URL=your_webhook_url
```

---

## Testing

Run the comprehensive pytest test suite (337 tests):

```bash
make test
```

---

## Safety

- **Research Platform Only** — Not financial advice.
- **Never Auto-Trades** — All trade execution is manual ("I Did This").
- **Risk Limits** — Enforced at position, sector, drawdown, and earnings blackout levels.

---

## License

MIT License. See [LICENSE](LICENSE).
