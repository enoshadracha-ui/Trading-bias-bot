import os
import asyncio
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
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run(telegram_app.process_update(update))
    return "ok"

@app.get("/set-webhook")
def set_webhook():
    if not RENDER_EXTERNAL_URL:
        return jsonify({"ok": False, "error": "RENDER_EXTERNAL_URL missing"}), 400
    url = RENDER_EXTERNAL_URL + WEBHOOK_PATH
    result = asyncio.run(telegram_app.bot.set_webhook(url=url))
    return jsonify({"ok": bool(result), "webhook": url})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
