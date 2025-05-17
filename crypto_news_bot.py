import os
import json
import feedparser
import telegram
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, time as dt_time
from flask import Flask, request
from openai import OpenAI
import tradingeconomics as te
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import threading
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# === КОНФИГ ===
TOKEN = "8165550696:AAFTSgRStivlcC0xlFgOiApubOl6VZJkWHk"
CHANNEL = "@AYE_ZHIZN_VORAM1312"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TE_API_KEY = "300d469a2fe04f2:7vk6trdkoxhwpak"

bot = telegram.Bot(token=TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
te.login(TE_API_KEY)

# === КЛЮЧЕВЫЕ СЛОВА ===
KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "binance", "airdrop",
    "token", "altcoin", "dex", "defi", "nft", "wallet", "solana", "sol",
    "cardano", "ada", "polygon", "matic", "layer2", "staking", "airdrops", "dao",
    "web3", "metaverse", "smart contracts", "mining", "hashrate", "block explorer",
    "ledger", "cold wallet", "hot wallet", "gas fees", "stablecoin", "usdt",
    "usdc", "tether", "block", "halving", "rug pull", "liquidity pool", "yield farming",
    "governance token", "launchpad", "whitelist", "ico", "ido", "ieo", "security token",
    "privacy coin", "zk rollup", "optimism", "arbitrum", "bsc", "evm", "oracle",
    "chainlink", "l2", "on-chain", "off-chain", "market cap", "crypto exchange",
    "tokenomics", "proof of stake", "proof of work", "hash function",
    "decentralized finance", "cross-chain", "interoperability", "gas", "wrapped token",
    "stable assets", "crypto wallet", "flash loan", "impermanent loss", "synthetic asset",
    "staking pool", "validator", "bridge", "rollup", "governance", "token swap",
    "cryptography", "public key", "private key", "hash", "trading bot", "volume",
    "altseason", "bull run", "bear market", "token burn", "KYC", "smart contract audit"
]

# === RSS-ИСТОЧНИКИ ===
FEEDS = [...]  # Список уже включён ранее

SENT_FILE = "sent_links.json"
app = Flask(__name__)
scheduler = BackgroundScheduler(timezone=pytz.utc)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def is_russian(text):
    return sum(c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for c in text.lower()) > 3

def translate(text):
    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Переведи на русский заголовок крипто-новости: {text}"}],
            max_tokens=60
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print("Ошибка перевода:", e)
        return text

def contains_keywords(text):
    return any(k.lower() in text.lower() for k in KEYWORDS)

def load_sent():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_sent(sent):
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent), f)

def check_feeds():
    sent = load_sent()
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title = entry.title
                link = entry.link
                if link not in sent and contains_keywords(title):
                    if not is_russian(title):
                        title = translate(title)
                    msg = f"<b>{title}</b>\n{link}"
                    bot.send_message(chat_id=CHANNEL, text=msg, parse_mode="HTML")
                    sent.add(link)
                    save_sent(sent)
        except Exception as e:
            print("RSS error:", e)

# === DIGEST ===
def send_daily_digest():
    today = date.today().strftime("%d.%m.%Y")
    msg = f"🗓️ <b>Важное на день ({today}):</b>\n- Подробности обновятся позже..."
    try:
        with open("daily.png", "rb") as img:
            bot.send_photo(chat_id=CHANNEL, photo=img, caption=msg, parse_mode="HTML")
    except Exception as e:
        print("❌ Ошибка при отправке дневной сводки:", e)

def send_weekly_digest():
    today = date.today().strftime("%d.%m.%Y")
    msg = f"📅 <b>Важное на неделю ({today}):</b>\n- Подробности обновятся позже..."
    try:
        with open("weekly.png", "rb") as img:
            bot.send_photo(chat_id=CHANNEL, photo=img, caption=msg, parse_mode="HTML")
    except Exception as e:
        print("❌ Ошибка при отправке недельной сводки:", e)

scheduler.add_job(send_daily_digest, trigger='cron', hour=7, minute=0)
scheduler.add_job(send_weekly_digest, trigger='cron', day_of_week='mon', hour=7, minute=30)
scheduler.add_job(check_feeds, 'interval', minutes=10)
scheduler.start()

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    if update.message and update.message.text:
        text = update.message.text
        if text == "/news":
            threading.Thread(target=check_feeds).start()
            bot.send_message(chat_id=update.message.chat.id, text="✅ Проверка запущена.")
        elif text == "/help":
            bot.send_message(chat_id=update.message.chat.id, text="/news — получить новости\n/help — помощь")
        elif text == "/menu":
            keyboard = [
                [InlineKeyboardButton("🔍 Проверить новости", callback_data='check_news')],
                [InlineKeyboardButton("📅 Сводка на день", callback_data='daily')],
                [InlineKeyboardButton("🗓️ Сводка на неделю", callback_data='weekly')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.send_message(chat_id=update.message.chat.id, text="📲 Выберите действие:", reply_markup=reply_markup)
    return "ok"

@app.route("/")
def index():
    return "✅ Бот работает!"

if __name__ == "__main__":
    bot.set_webhook(f"https://crypto-news-bot-render.onrender.com/{TOKEN}")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
