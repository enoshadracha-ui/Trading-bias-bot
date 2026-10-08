# Trading Bias Bot

A Telegram bot that performs a manual Daily + 4H market-bias scan.

## What it does

The bot is intentionally bias-only.

It does NOT:
- find entry prices
- give stop loss
- give take profit
- execute trades
- manage trades
- scan continuously

Commands:
- `/start`
- `/status`
- `/bias`

`/bias` makes one Daily batch request and one 4H batch request to Twelve Data, then analyzes every configured instrument.

Twelve Data documents support for `1day` and `4h` intervals and batch symbol requests.

## Strategy logic implemented

1. Daily:
   - Use the line-chart structure to form A-Shape resistance, V-Shape support,
     RBS, SBR, and OCL-style levels.
   - Require the latest completed Daily candle to interact with a valid level
     and reject/close away from it.
   - This creates the directional Daily bias.

2. 4H:
   - The breakout must be a directional displacement sequence, not a single
     isolated candle.
   - The sequence must contain multiple directional candles.
   - The same breakout sequence must create at least one meaningful FVG/imbalance.
   - Either confirmation is sufficient:
       A. liquidity sweep + breakout, with inefficient price action
       OR
       B. most recent breakout, with inefficient price action.

3. The bot stops at bias:
   - It does NOT detect the later retracement.
   - It does NOT find an entry.
   - It does NOT calculate SL/TP.
   - It does NOT execute or manage trades.

4. Output:
   - BULLISH BIAS
   - BEARISH BIAS
   - NO BIAS

## Important strategy-definition note

Your descriptions of A-Shape, V-Shape, RBS, SBR, OCL and inefficient price action were conceptual rather than fully mathematical. This version therefore uses configurable mechanical proxies in `analyzer.py`.

If you later give exact rules for those structures, replace the proxy functions without changing the Telegram/Render/API layer.

## Instruments

- EUR/CHF
- GBP/USD
- AUD/NZD
- EUR/USD
- AUD/CHF
- GBP/AUD
- EUR/CAD
- XAU/USD — Gold
- Nasdaq 100 Index
- USD/CAD
- FTSE 100 Index — UK 100
- Japan 225 CFD — JP 225
- GBP/CAD

The three index symbols are kept configurable because data vendors can use different symbols for index/CFD instruments.

## Local setup

Python 3.13 recommended.

```bash
pip install -r requirements.txt
```

Set:

```text
TELEGRAM_BOT_TOKEN=...
TWELVE_DATA_API_KEY=...
RENDER_EXTERNAL_URL=https://your-service.onrender.com
```

Run:

```bash
python bot.py
```

## Render

Create a Web Service from the GitHub repository.

Build:
```text
pip install -r requirements.txt
```

Start:
```text
gunicorn -w 1 -b 0.0.0.0:$PORT bot:app
```

Add the three environment variables.

After deployment, open:

```text
https://YOUR-SERVICE.onrender.com/set-webhook
```

Then open the Telegram bot and use `/start`.

## API usage

The bot does not continuously poll market data.

Each `/bias` command uses:
- 1 Daily batch request
- 1 4H batch request

The exact API credit cost depends on the provider plan and symbol availability.
