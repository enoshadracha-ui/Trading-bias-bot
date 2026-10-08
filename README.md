# Trading Bias Bot

Bias-only Telegram bot. It does not place trades and does not provide entries, SL or TP.

## Commands
- /start
- /status
- /bias

## Render environment variables
- TELEGRAM_BOT_TOKEN
- TWELVE_DATA_API_KEY
- RENDER_EXTERNAL_URL

Set RENDER_EXTERNAL_URL to the exact Render service URL, for example:
https://trading-bias-bot.onrender.com

## Deployment
Build:
pip install -r requirements.txt

Start:
gunicorn -w 1 -b 0.0.0.0:$PORT bot:app

After deployment:
1. Open /set-webhook once.
2. Confirm it returns ok:true.
3. Optionally open /webhook-info to inspect Telegram's webhook status.
4. Test /start, /status and /bias in Telegram.

Never put API keys or bot tokens in GitHub.
