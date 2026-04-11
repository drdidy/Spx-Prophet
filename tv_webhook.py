"""
SPX PROPHET — TradingView Webhook Bridge
Receives alerts from TradingView and stores them for
the Streamlit dashboard to display.

SETUP IN TRADINGVIEW:
1. Create an alert on your ES chart
2. Set webhook URL to: http://YOUR_IP:8501/webhook
3. Set the alert message to JSON format:
   {
     "action": "{{strategy.order.action}}",
     "price": "{{close}}",
     "time": "{{time}}",
     "ticker": "{{ticker}}",
     "message": "Your custom note"
   }
4. Or for manual price alerts:
   {
     "action": "ALERT",
     "price": "{{close}}",
     "message": "Price hit my level"
   }

NO LOGIN CREDENTIALS NEEDED. TradingView pushes to your URL.
"""

import json
import datetime as dt
from dataclasses import dataclass, field
from typing import List, Optional
import threading

import pytz

from config import TV_WEBHOOK_SECRET, TIMEZONE

CT = pytz.timezone(TIMEZONE)


@dataclass
class TVAlert:
    timestamp: dt.datetime
    action: str          # "buy", "sell", "ALERT", etc.
    price: float
    ticker: str
    message: str
    raw_data: dict = field(default_factory=dict)


# In-memory alert store (shared across threads)
_alerts: List[TVAlert] = []
_alerts_lock = threading.Lock()


def add_alert(alert: TVAlert):
    """Thread-safe alert addition."""
    with _alerts_lock:
        _alerts.append(alert)
        # Keep only last 50 alerts
        if len(_alerts) > 50:
            _alerts.pop(0)


def get_alerts(limit: int = 20) -> List[TVAlert]:
    """Get recent alerts."""
    with _alerts_lock:
        return list(reversed(_alerts[-limit:]))


def clear_alerts():
    """Clear all stored alerts."""
    with _alerts_lock:
        _alerts.clear()


def parse_tv_webhook(data: dict, secret: str = "") -> Optional[TVAlert]:
    """
    Parse incoming TradingView webhook payload.
    Returns TVAlert or None if invalid.
    """
    # Optional secret validation
    if secret and data.get("secret") != secret:
        return None

    try:
        price = float(data.get("price", 0))
    except (ValueError, TypeError):
        price = 0.0

    alert = TVAlert(
        timestamp=dt.datetime.now(CT),
        action=str(data.get("action", "ALERT")).upper(),
        price=price,
        ticker=str(data.get("ticker", "ES")),
        message=str(data.get("message", "")),
        raw_data=data,
    )

    return alert


def start_webhook_server(port: int = 8501):
    """
    Start a simple HTTP server to receive TradingView webhooks.
    Runs in a background thread so it doesn't block Streamlit.

    NOTE: This is a simple implementation. For production,
    use ngrok or a cloud endpoint to expose your local port.
    """
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class WebhookHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/webhook":
                self.send_response(404)
                self.end_headers()
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                data = json.loads(body)
                alert = parse_tv_webhook(data, TV_WEBHOOK_SECRET)
                if alert:
                    add_alert(alert)
                    self.send_response(200)
                    self.wfile.write(b'{"status":"ok"}')
                else:
                    self.send_response(401)
                    self.wfile.write(b'{"error":"invalid"}')
            except json.JSONDecodeError:
                self.send_response(400)
                self.wfile.write(b'{"error":"bad json"}')

            self.end_headers()

        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"prophet_alive"}')
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>SPX Prophet Webhook</h1><p>POST to /webhook</p>")

        def log_message(self, format, *args):
            pass  # Suppress logs

    try:
        server = HTTPServer(("0.0.0.0", port), WebhookHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return True
    except OSError:
        # Port already in use (probably already started)
        return False


# ─── Notification Sound (HTML5 Audio via Streamlit) ───────────────────

def get_notification_html(signal_type: str = "signal") -> str:
    """
    Returns HTML that plays a notification sound via Web Audio API.
    No external files needed — generates a tone programmatically.
    """
    if signal_type == "long":
        freq, duration = 880, 0.15  # High A, short chirp
        pattern = "0.15,0.05,0.15"   # chirp-chirp
    elif signal_type == "short":
        freq, duration = 440, 0.2   # Middle A, longer
        pattern = "0.2,0.08,0.2"
    elif signal_type == "alert":
        freq, duration = 660, 0.3   # Alert tone
        pattern = "0.3"
    else:
        freq, duration = 550, 0.15
        pattern = "0.15"

    return f"""
    <script>
    (function() {{
        try {{
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const durations = [{pattern}];
            let time = ctx.currentTime;
            durations.forEach((d, i) => {{
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.frequency.value = {freq};
                osc.type = 'sine';
                gain.gain.setValueAtTime(0.3, time);
                gain.gain.exponentialRampToValueAtTime(0.01, time + d);
                osc.start(time);
                osc.stop(time + d);
                time += d + 0.05;
            }});
        }} catch(e) {{}}
    }})();
    </script>
    """
