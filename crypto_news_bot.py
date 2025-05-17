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

# === КОНФИГ ===
TOKEN = "8165550696:AAFTSgRStivlcC0xlFgOiApubOl6VZJkWHk"
CHANNEL = "@AYE_ZHIZN_VORAM1312"
TE_API_KEY = "300d469a2fe04f2:7vk6trdkoxhwpak"

bot = telegram.Bot(token=TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
te.login(TE_API_KEY)

# === КЛЮЧЕВЫЕ СЛОВА ===
KEYWORDS = [...]

# === RSS-ИСТОЧНИКИ ===
FEEDS = [...]

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
    updated = False
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                title = entry.title
                link = entry.link
                if link not in sent and contains_keywords(title):
                    if not is_russian(title):
                        title = translate(title)
                    msg = f"<b>{title}</b>\n{link}"
                    bot.send_message(chat_id=CHANNEL, text=msg, parse_mode="HTML")
                    sent.add(link)
                    updated = True
        except Exception as e:
            print("RSS error:", e)
    if updated:
        save_sent(sent)

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
        if update.message.text == "/news":
            check_feeds()
            bot.send_message(chat_id=update.message.chat.id, text="✅ Новости отправлены.")
        elif update.message.text == "/help":
            bot.send_message(chat_id=update.message.chat.id, text="/news — получить новости\n/help — помощь")
    return "ok"

@app.route("/")
def index():
    return "✅ Бот работает!"

if __name__ == "__main__":
    bot.set_webhook(f"https://crypto-news-bot-render.onrender.com/{TOKEN}")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
