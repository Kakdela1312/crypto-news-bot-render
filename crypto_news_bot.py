import os
import json
import feedparser
import telegram
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, request
from openai import OpenAI
import tradingeconomics as te

# 🔐 КЛЮЧИ
TELEGRAM_TOKEN = "8165550696:AAFTSgRStivlcC0xlFgOiApubOl6VZJkWHk"
TELEGRAM_CHANNEL = "@AYE_ZHIZN_VORAM1312"
OPENAI_API_KEY = "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"
TE_API_KEY = "300d469a2fe04f2:7vk6trdkoxhwpak"

# 🔧 ИНИЦИАЛИЗАЦИЯ
bot = telegram.Bot(token=TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
te.login(TE_API_KEY)

# 📰 КЛЮЧЕВЫЕ СЛОВА
KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "binance", "airdrop",
    "token", "altcoin", "dex", "defi", "nft", "wallet", "solana", "sol",
    "cardano", "ada", "polygon", "matic", "layer2", "staking"
]

# 🔗 RSS-КАНАЛЫ
FEEDS = [
    "https://forklog.com/feed",
    "https://cryptonews.net/ru/news/feed/",
    "https://cointelegraph.com/rss",
    "https://www.newsbtc.com/feed/",
    "https://decrypt.co/feed",
    "https://cryptopotato.com/feed/",
    "https://www.coindesk.com/arc/outboundfeeds/rss/"
]

SENT_FILE = "sent_links.json"
app = Flask(__name__)

# 🔤 Проверка языка
def is_russian(text):
    return sum(c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for c in text.lower()) > 3

# 🌐 Перевод
def translate(text):
    try:
        print("🔁 Переводим:", text)
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Переведи на русский заголовок крипто-новости: {text}"}],
            max_tokens=60
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print("❌ Ошибка перевода:", e)
        return text

# 🔎 Ключевые слова
def contains_keywords(text):
    return any(k in text.lower() for k in KEYWORDS)

# 💾 Загруженные ссылки
def load_sent():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_sent(sent):
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent), f)

# ✅ Проверка фидов
def check_feeds():
    sent = load_sent()
    updated = False
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                title = entry.title
                link = entry.link
                if link not in sent and contains_keywords(title):
                    if not is_russian(title):
                        title = translate(title)
                    msg = f"📰 <b>{title}</b>\n{link}"
                    bot.send_message(chat_id=TELEGRAM_CHANNEL, text=msg, parse_mode="HTML")
                    sent.add(link)
                    updated = True
        except Exception as e:
            print("❌ Ошибка RSS:", e)
    if updated:
        save_sent(sent)

# 📩 Обработка запросов от Telegram
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    if update.message and update.message.text:
        if update.message.text == "/news":
            check_feeds()
            bot.send_message(chat_id=update.message.chat.id, text="✅ Новости отправлены.")
        elif update.message.text == "/help":
            bot.send_message(chat_id=update.message.chat.id, text="/news — получить новости\n/help — помощь")
    return "ok"

@app.route("/")
def index():
    return "✅ Бот работает!"

# 🚀 Старт
if __name__ == "__main__":
    bot.set_webhook(f"https://crypto-news-bot-render.onrender.com/{TELEGRAM_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
