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
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# === КОНФИГ ===
TOKEN = "8165550696:AAFTSgRStivlcC0xlFgOiApubOl6VZJkWHk"
CHANNEL = "@AYE_ZHIZN_VORAM1312"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TE_API_KEY = "300d469a2fe04f2:7vk6trdkoxhwpak"

bot = telegram.Bot(token=TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
te.login(TE_API_KEY)

timezone = pytz.timezone("Europe/Sofia")

# === ГЛОБАЛЬНЫЕ НАСТРОЙКИ ===
settings = {
    "autotranslate": True
}

# === КЛЮЧЕВЫЕ СЛОВА ===
KEYWORDS = ["bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "binance", "airdrop"]

# === RSS-ИСТОЧНИКИ ===
FEEDS = ["https://forklog.com/feed", "https://cointelegraph.com/rss"]

SENT_FILE = "sent_links.json"
app = Flask(__name__)
scheduler = BackgroundScheduler(timezone=timezone)

# === ФУНКЦИИ ===
def is_russian(text):
    return sum(c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for c in text.lower()) > 3

def translate(text):
    if not settings["autotranslate"]:
        return text
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
            for entry in feed.entries:
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

def send_daily_digest():
    today = datetime.now(timezone).strftime("%d.%m.%Y")
    msg = f"🗓️ <b>Важное на день ({today}):</b>\n- Подробности обновятся позже..."
    try:
        with open("daily.png", "rb") as img:
            bot.send_photo(chat_id=CHANNEL, photo=img, caption=msg, parse_mode="HTML")
    except Exception as e:
        print("❌ Ошибка при отправке дневной сводки:", e)

def send_weekly_digest():
    today = datetime.now(timezone).strftime("%d.%m.%Y")
    msg = f"📅 <b>Важное на неделю ({today}):</b>\n- Подробности обновятся позже..."
    try:
        with open("weekly.png", "rb") as img:
            bot.send_photo(chat_id=CHANNEL, photo=img, caption=msg, parse_mode="HTML")
    except Exception as e:
        print("❌ Ошибка при отправке недельной сводки:", e)

def send_menu(chat_id):
    keyboard = [
        [InlineKeyboardButton("📥 Проверить новости", callback_data='check_news')],
        [InlineKeyboardButton("📅 Сводка на неделю", callback_data='weekly_digest')],
        [InlineKeyboardButton("🗓️ Сводка на день", callback_data='daily_digest')],
        [InlineKeyboardButton("🔁 Перевод: " + ("ВКЛ" if settings["autotranslate"] else "ВЫКЛ"), callback_data='toggle_translate')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id=chat_id, text="Выберите действие:", reply_markup=reply_markup)

# === ЗАДАЧИ ===
scheduler.add_job(send_daily_digest, trigger='cron', hour=7, minute=0)
scheduler.add_job(send_weekly_digest, trigger='cron', day_of_week='mon', hour=7, minute=30)
scheduler.add_job(check_feeds, 'interval', minutes=10)
scheduler.start()

# === ВЕБХУК ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    if update.message:
        if update.message.text == "/start":
            send_menu(update.message.chat.id)
        elif update.message.text == "/news":
            check_feeds()
            bot.send_message(chat_id=update.message.chat.id, text="✅ Новости отправлены.")
        elif update.message.text == "/help":
            bot.send_message(chat_id=update.message.chat.id, text="/news — получить новости\n/help — помощь\n/digest — сводка")
        elif update.message.text == "/digest":
            send_daily_digest()
            send_weekly_digest()
            bot.send_message(chat_id=update.message.chat.id, text="📌 Сводки отправлены.")

    elif update.callback_query:
        query = update.callback_query
        if query.data == "check_news":
            check_feeds()
            query.answer("Проверка завершена")
        elif query.data == "weekly_digest":
            send_weekly_digest()
            query.answer("Отправлена сводка на неделю")
        elif query.data == "daily_digest":
            send_daily_digest()
            query.answer("Отправлена сводка на день")
        elif query.data == "toggle_translate":
            settings["autotranslate"] = not settings["autotranslate"]
            query.answer("Автоперевод: " + ("ВКЛ" if settings["autotranslate"] else "ВЫКЛ"))
            send_menu(query.message.chat.id)

    return "ok"

@app.route("/")
def index():
    return "✅ Бот работает!"

if __name__ == "__main__":
    bot.set_webhook(f"https://crypto-news-bot-render.onrender.com/{TOKEN}")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
