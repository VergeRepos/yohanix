"""Discord webhook alert sender (optional)."""
import logging
import requests
from datetime import datetime
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
    """Send or edit previous Discord webhook message every 30s to prevent channel flooding."""
    url = get_config().get("discord_webhook_url", "")
    if not url:
        return False
    try:
        from pathlib import Path
        import json
        project_root = Path(__file__).resolve().parent.parent.parent
        json_dir = project_root / "outputs" / "json"
        state_file = project_root / "outputs" / ".discord_message_id.json"

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

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S ET")
        payload = {
            "embeds": [{
                "title": "📊 Yohanix Live Market Top 10 Report",
                "description": f"Automated 30-sec live update (Refreshed: {timestamp}). Total scanned: {len(recs)} tickers.",
                "color": 0x0099FF,
                "fields": fields if fields else [{"name": "Status", "value": "No scan data found yet. Run a scan.", "inline": False}]
            }]
        }

        # Load last message id
        message_id = None
        if state_file.exists():
            try:
                with open(state_file) as sf:
                    message_id = json.load(sf).get("message_id")
            except Exception:
                pass

        success = False
        if message_id:
            patch_url = f"{url.rstrip('/')}/messages/{message_id}"
            try:
                resp = requests.patch(patch_url, json=payload, timeout=10)
                if resp.status_code == 200:
                    success = True
            except Exception:
                pass

        if not success:
            wait_url = f"{url}?wait=true" if "?" not in url else f"{url}&wait=true"
            resp = requests.post(wait_url, json=payload, timeout=10)
            resp.raise_for_status()
            res_data = resp.json()
            new_id = res_data.get("id")
            if new_id:
                state_file.parent.mkdir(parents=True, exist_ok=True)
                with open(state_file, "w") as sf:
                    json.dump({"message_id": new_id}, sf)
            success = True

        logger.info("Discord periodic update sent/edited successfully (%d tickers)", len(top10))
        return True
    except Exception:
        logger.exception("Discord periodic update failed")
        return False


def send_discord_trade_list() -> dict:
    """Send the entire ordered list of trades (Buy to Caution/Sell) to Discord."""
    url = get_config().get("discord_webhook_url", "")
    if not url:
        return {"success": False, "error": "Discord webhook URL not configured in .env"}
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

        if not recs:
            return {"success": False, "error": "No scan data found. Run a scan first."}

        action_order = {"BUY": 0, "WATCHLIST": 1, "HOLD": 2, "CAUTION": 3, "SELL": 4}
        sorted_recs = sorted(
            recs,
            key=lambda r: (action_order.get(r.get("action", "HOLD"), 5), -r.get("composite_score", 0))
        )

        fields = []
        for r in sorted_recs[:20]:
            ticker = r.get("ticker", "???")
            action = r.get("action", "HOLD")
            score = r.get("composite_score", 0)
            conf = r.get("confidence", 0)
            thesis = r.get("thesis", "No thesis provided.")[:100]
            emoji = {"BUY": "🟢", "SELL": "🔴", "WATCHLIST": "🔵", "HOLD": "🟡", "CAUTION": "🟠"}.get(action, "⚪")
            fields.append({
                "name": f"{emoji} {ticker} — {action} (Score: {score:+.1f} | Conf: {conf}%)",
                "value": thesis,
                "inline": False
            })

        payload = {
            "embeds": [{
                "title": "📋 Yohanix Ordered Trade Execution Plan (Buy → Caution)",
                "description": f"Manually pushed complete ranked trade list. Total candidates: {len(sorted_recs)}.",
                "color": 0x22C55E,
                "fields": fields
            }]
        }

        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return {"success": True, "count": len(sorted_recs)}
    except Exception as e:
        logger.exception("Failed to send trade list to Discord")
        return {"success": False, "error": str(e)}
