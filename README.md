# SPX Prophet — Legendary Edition

Private trading system. Do not share or make public.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

App runs at `http://localhost:8501`

## File Map

| File | Purpose |
|---|---|
| `app.py` | Main application, 9 tabs, sidebar controls |
| `config.py` | All constants and parameters |
| `styles.py` | UI styling and animations |
| `data_fetcher.py` | yfinance data + demo fallback |
| `pivot_detector.py` | Pivot identification logic |
| `line_calculator.py` | 4-line math with market-hours correction |
| `signal_engine.py` | Signal detection + session quality score |
| `macro_calendar.py` | 150 economic events (2025-2026) |
| `backtester.py` | Historical strategy backtester |
| `options_calculator.py` | 0DTE SPX options P&L estimator |
| `monte_carlo.py` | Forward probability simulation |
| `journal.py` | Persistent CSV trade journal |
| `tv_webhook.py` | TradingView webhook + sound alerts |
| `ui_components.py` | Dashboard rendering functions |

## TradingView Webhook Setup

1. Enable webhook in the app sidebar (TV ALERTS section)
2. Install ngrok and expose your local port:
   ```bash
   ngrok http 8501
   ```
3. Copy the ngrok URL (e.g. `https://abc123.ngrok.io`)
4. In TradingView, create an alert on your ES chart
5. Set webhook URL to: `https://abc123.ngrok.io/webhook`
6. Set alert message to:
   ```json
   {
     "action": "{{strategy.order.action}}",
     "price": "{{close}}",
     "ticker": "{{ticker}}",
     "message": "Your note here"
   }
   ```
7. Alerts appear in the TV ALERTS tab in real time

No TradingView login or API key needed. TV pushes to your URL.

## Deploy to Streamlit Cloud

1. Push this repo to GitHub (keep it **private**)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select `spx-prophet` repo, `main` branch, `app.py`
5. Deploy

Streamlit Cloud can deploy from private repos if your GitHub account is connected.

## Trade Journal

Trades save to `prophet_journal.csv` in the app directory. This file persists across sessions. You can download it from the Journal tab or back it up manually.

## Key Files to Back Up

- `prophet_journal.csv` — your trade history
- `config.py` — if you change any parameters

## Notes

- Data comes from Yahoo Finance. ES futures (`ES=F`) are real-time during market hours
- If yfinance can't connect, the app falls back to demo data automatically
- Line calculations exclude the 4-5 PM CT maintenance window and weekend gaps
- All times are US/Central
