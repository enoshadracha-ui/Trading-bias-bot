import os
import asyncio
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError

import requests
from flask import Flask, jsonify, request
from telegram import Update
from telegram.ext import Application, CommandHandler

from analyzer import scan_all
from config import INSTRUMENTS

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "10000"))
PUBLIC_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_PATH = "/webhook"

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

if not PUBLIC_URL:
    raise RuntimeError("RENDER_EXTERNAL_URL is missing")

app = Flask(__name__)

# We use python-telegram-bot's Application only for handlers and processing.
# The Flask server owns the HTTP webhook endpoint.
telegram_app = Application.builder().token(TOKEN).updater(None).build()


async def start(update: Update, context):
    await update.message.reply_text(
        "Trading Bias Bot is ready.\n\n"
        "Use /bias to scan all 13 instruments once.\n"
        "Use /status to check the bot."
    )


async def status(update: Update, context):
    await update.message.reply_text(
        f"Bot is running.\n"
        f"Configured instruments: {len(INSTRUMENTS)}\n"
        "Scan mode: manual only."
    )


async def bias(update: Update, context):
    await update.message.reply_text(
        "Scanning Daily + 4H data. Please wait..."
    )
    try:
        results = await asyncio.to_thread(scan_all)
        confirmed = [
            r for r in results if r.get("bias") in ("BULLISH BIAS", "BEARISH BIAS")
        ]

        if not confirmed:
            text = "NO CONFIRMED BIAS"
        else:
            lines = ["TRADING BIAS RESULTS", ""]
            for r in confirmed:
                lines.append(f'{r["display"]} — {r["bias"]}')
            text = "\n".join(lines)

        await update.message.reply_text(text)
    except Exception:
        print("SCAN ERROR", flush=True)
        await update.message.reply_text(
            "The scan could not be completed. Check the Render logs."
        )


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("status", status))
telegram_app.add_handler(CommandHandler("bias", bias))


# Dedicated asyncio loop for the Telegram application.
bot_loop = asyncio.new_event_loop()
bot_started = threading.Event()
bot_error = {"value": None}


def run_telegram_application():
    asyncio.set_event_loop(bot_loop)
    try:
        bot_loop.run_until_complete(telegram_app.initialize())
        bot_loop.run_until_complete(telegram_app.start())
        bot_started.set()
        bot_loop.run_forever()
    except Exception as exc:
        bot_error["value"] = repr(exc)
        print(f"TELEGRAM APP START ERROR: {exc!r}", flush=True)
        bot_started.set()


threading.Thread(
    target=run_telegram_application,
    name="telegram-application",
    daemon=True,
).start()

bot_started.wait(timeout=20)


def submit_update(update):
    if bot_error["value"]:
        raise RuntimeError(bot_error["value"])
    future = asyncio.run_coroutine_threadsafe(
        telegram_app.update_queue.put(update),
        bot_loop,
    )
    return future.result(timeout=10)


@app.get("/")
def health():
    return jsonify({
        "ok": True,
        "service": "Trading Bias Bot",
        "scan_mode": "manual",
        "instruments": len(INSTRUMENTS),
        "webhook_path": WEBHOOK_PATH,
    })


@app.post(WEBHOOK_PATH)
def webhook():
    try:
        payload = request.get_json(force=True)
        update = Update.de_json(payload, telegram_app.bot)
        submit_update(update)
        return "ok", 200
    except Exception as exc:
        print(f"WEBHOOK ERROR: {exc!r}", flush=True)
        return jsonify({"ok": False}), 500


@app.get("/set-webhook")
def set_webhook():
    """Set Telegram's webhook with direct HTTPS requests and short retries."""
    webhook_url = PUBLIC_URL + WEBHOOK_PATH
    api_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"

    last_error = None

    for attempt in range(1, 4):
        try:
            response = requests.post(
                api_url,
                data={
                    "url": webhook_url,
                    "allowed_updates": '["message"]',
                },
                timeout=(8, 20),
            )
            data = response.json()
            print(f"SET WEBHOOK RESPONSE: {data}", flush=True)

            if data.get("ok"):
                return jsonify({
                    "ok": True,
                    "webhook": webhook_url,
                })

            return jsonify({
                "ok": False,
                "telegram_response": data,
            }), 502

        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(
                f"SET WEBHOOK ATTEMPT {attempt} ERROR: {last_error}",
                flush=True,
            )

    return jsonify({
        "ok": False,
        "error": "Render could not reach Telegram's API.",
        "details": last_error,
    }), 504


@app.get("/webhook-info")
def webhook_info():
    """Read Telegram webhook status without exposing the token."""
    api_url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
    try:
        response = requests.get(api_url, timeout=(8, 20))
        data = response.json()
        if data.get("ok"):
            info = data.get("result", {})
            return jsonify({
                "ok": True,
                "url": info.get("url", ""),
                "pending_update_count": info.get("pending_update_count", 0),
                "last_error_date": info.get("last_error_date"),
                "last_error_message": info.get("last_error_message"),
            })
        return jsonify({"ok": False, "telegram_response": data}), 502
    except requests.RequestException as exc:
        return jsonify({
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }), 504


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
