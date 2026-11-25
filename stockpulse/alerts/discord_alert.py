"""Discord webhook alert sender (optional)."""
import logging
import requests
from stockpulse.config.settings import get_config

logger = logging.getLogger(__name__)

def _format_embed(alert: dict) -> dict:
    ticker = alert.get("ticker", "???")
    action = alert.get("action", "???")
    confidence = alert.get("confidence", 0)
    color = {"BUY": 0x00FF00, "SELL": 0xFF0000, "HOLD": 0xFFFF00,
             "WATCHLIST": 0x0099FF, "CAUTION": 0xFF8C00}.get(action, 0x808080)
    return {"embeds": [{"title": f"Yohanix: {ticker} -- {action}", "description": alert.get("thesis", ""),
        "color": color, "fields": [
            {"name": "Confidence", "value": f"{confidence}%", "inline": True},
            {"name": "Type", "value": alert.get("type", "signal"), "inline": True},
            {"name": "Technical", "value": alert.get("technical_summary", "N/A")[:200], "inline": False},
            {"name": "Catalysts", "value": alert.get("catalyst_summary", "N/A")[:200], "inline": False},
            {"name": "Invalidation", "value": alert.get("invalidation", "N/A")[:200], "inline": False},
        ]}]}

def send_discord_alert(alert: dict) -> bool:
    cfg = get_config()
    if not cfg["alerts_discord"]:
        return False
    url = cfg["discord_webhook_url"]
    if not url:
        logger.warning("Discord enabled but webhook URL not configured")
        return False
    try:
        payload = _format_embed(alert)
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception("Discord alert failed")
        return False


def send_discord_periodic_update() -> bool:
    url = get_config().get("discord_webhook_url", "")
    if not url:
        return False
    try:
        from pathlib import Path
        import json
        project_root = Path(__file__).resolve().parent.parent.parent
        json_dir = project_root / "outputs" / "json"
        recs = []
        if json_dir.exists():
            files = sorted(json_dir.glob("*.json"), reverse=True)
            for f in files:
                try:
                    with open(f) as fh:
                        data = json.load(fh)
                        if isinstance(data, dict) and "recommendations" in data:
                            recs = data.get("recommendations", [])
                            break
                except Exception:
                    continue

        top10 = sorted(recs, key=lambda r: abs(r.get("composite_score", 0)), reverse=True)[:10]
        fields = []
        for r in top10:
            ticker = r.get("ticker", "???")
            action = r.get("action", "HOLD")
            score = r.get("composite_score", 0)
            conf = r.get("confidence", 0)
            thesis = r.get("thesis", "No thesis provided.")[:120]
            emoji = {"BUY": "🟢", "SELL": "🔴", "WATCHLIST": "🔵", "HOLD": "🟡", "CAUTION": "🟠"}.get(action, "⚪")
            fields.append({
                "name": f"{emoji} {ticker} — {action} (Score: {score:+.1f} | Conf: {conf}%)",
                "value": thesis,
                "inline": False
            })

        payload = {
            "embeds": [{
                "title": "📊 Yohanix Live Market Top 10 Report",
                "description": f"Automated 1-minute live update (BUY, SELL, WATCHLIST, HOLD). Total scanned: {len(recs)} tickers.",
                "color": 0x0099FF,
                "fields": fields if fields else [{"name": "Status", "value": "No scan data found yet. Run a scan via Make or UI.", "inline": False}]
            }]
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Discord periodic top 10 update sent successfully (%d tickers)", len(top10))
        return True
    except Exception:
        logger.exception("Discord periodic update failed")
        return False
