import os
import asyncio
import threading
import atexit
from concurrent.futures import TimeoutError as FutureTimeoutError

from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from analyzer import scan_all
from config import INSTRUMENTS

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PORT = int(os.getenv("PORT", "10000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_PATH = "/webhook"

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

app = Flask(__name__)

telegram_app = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Trading Bias Bot is ready.\n\n"
        "Use /bias to run one manual scan of all configured instruments.\n"
        "Use /status to check the bot."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Bot is running.\nConfigured instruments: {len(INSTRUMENTS)}\n"
        "Scanning mode: manual only (/bias)."
    )

async def bias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning Daily + 4H data. Please wait...")
    try:
        results = await asyncio.to_thread(scan_all)
        lines = ["TRADING BIAS RESULTS", ""]
        for r in results:
            if r["bias"] != "NO BIAS":
                lines.append(f'{r["display"]} — {r["bias"]}')
        if len(lines) == 2:
            lines.append("NO CONFIRMED BIAS")
        await update.message.reply_text("\n".join(lines))
    except Exception as exc:
        await update.message.reply_text(
            "Scan failed safely. Check the market-data API settings and Render logs."
        )
        print("SCAN ERROR:", repr(exc))

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("status", status))
telegram_app.add_handler(CommandHandler("bias", bias))

# Run the Telegram Application on one dedicated asyncio event loop.
# Flask/Gunicorn can then safely hand webhook updates to that loop.
bot_loop = asyncio.new_event_loop()
bot_ready = threading.Event()
bot_start_error = {"error": None}

def bot_loop_worker():
    asyncio.set_event_loop(bot_loop)
    try:
        bot_loop.run_until_complete(telegram_app.initialize())
        bot_loop.run_until_complete(telegram_app.start())
        bot_ready.set()
        bot_loop.run_forever()
    except Exception as exc:
        bot_start_error["error"] = repr(exc)
        bot_ready.set()
        print("TELEGRAM START ERROR:", repr(exc))
    finally:
        try:
            if telegram_app.running:
                bot_loop.run_until_complete(telegram_app.stop())
        except Exception as exc:
            print("TELEGRAM STOP ERROR:", repr(exc))
        try:
            bot_loop.run_until_complete(telegram_app.shutdown())
        except Exception as exc:
            print("TELEGRAM SHUTDOWN ERROR:", repr(exc))

threading.Thread(
    target=bot_loop_worker,
    name="telegram-bot-loop",
    daemon=True,
).start()

bot_ready.wait(timeout=20)

def run_on_bot_loop(coro, timeout=30):
    if bot_start_error["error"]:
        raise RuntimeError(bot_start_error["error"])
    future = asyncio.run_coroutine_threadsafe(coro, bot_loop)
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        future.cancel()
        raise TimeoutError("Telegram operation timed out")

@atexit.register
def stop_bot_loop():
    if bot_loop.is_running():
        bot_loop.call_soon_threadsafe(bot_loop.stop)

@app.get("/")
def health():
    return jsonify({
        "ok": True,
        "service": "Trading Bias Bot",
        "scan_mode": "manual",
        "instruments": len(INSTRUMENTS),
    })

@app.post(WEBHOOK_PATH)
def webhook():
    try:
        payload = request.get_json(force=True)
        update = Update.de_json(payload, telegram_app.bot)
        run_on_bot_loop(telegram_app.process_update(update), timeout=60)
        return "ok"
    except Exception as exc:
        print("WEBHOOK ERROR:", repr(exc))
        return jsonify({"ok": False, "error": "webhook processing failed"}), 500

@app.get("/set-webhook")
def set_webhook():
    if not RENDER_EXTERNAL_URL:
        return jsonify({"ok": False, "error": "RENDER_EXTERNAL_URL missing"}), 400
    url = RENDER_EXTERNAL_URL + WEBHOOK_PATH
    try:
        result = run_on_bot_loop(telegram_app.bot.set_webhook(url=url), timeout=30)
        return jsonify({"ok": bool(result), "webhook": url})
    except Exception as exc:
        print("SET WEBHOOK ERROR:", repr(exc))
        return jsonify({"ok": False, "error": "could not set webhook"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
