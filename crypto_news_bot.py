import feedparser
import telegram
from telegram.ext import Updater, CommandHandler
import time
import json
import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI
import tradingeconomics as te
import threading

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = "8106822791:AAFpNW8FHJZOmJ8HwCgBHeC9gQ5NOnvAdLc"
TELEGRAM_CHANNEL = "@AYE_ZHIZN_VORAM1312"
OPENAI_API_KEY = "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"
TE_API_KEY = "300d469a2fe04f2:7vk6trdkoxhwpak"
CHECK_INTERVAL = 600
SENT_FILE = "sent_combined_news.json"

client = OpenAI(api_key=OPENAI_API_KEY)
bot = telegram.Bot(token=TELEGRAM_TOKEN)
te.login(TE_API_KEY)

def is_silent_hours():
    h = datetime.now().hour
    return h >= 22 or h < 9

def send_financial_calendar():
    today = datetime.today().strftime('%Y-%m-%d')
    try:
        events = te.getCalendarData(initDate=today, endDate=today)
        message = f"📅 #ФинКалендарь на {today}\n\n"
        for event in events:
            if event.get("Importance") == "High":
                t = event.get("Date", "").split("T")[1][:5]
                title = event.get("Event", "")
                country = event.get("Country", "")
                message += f"- {t} — {title} ({country})\n"
        bot.send_message(chat_id=TELEGRAM_CHANNEL, text=message)
    except Exception as e:
        print("[Ошибка календаря]", e)

def send_infographics():
    try:
        url = "https://alternative.me/crypto/fear-and-greed-index.png"
        img = requests.get(url).content
        bot.send_photo(chat_id=TELEGRAM_CHANNEL, photo=img, caption="📊 Индекс страха и жадности")
    except Exception as e:
        print("[Ошибка страха/жадности]", e)
    try:
        for file in os.listdir("analytics"):
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                with open(os.path.join("analytics", file), "rb") as img:
                    bot.send_photo(chat_id=TELEGRAM_CHANNEL, photo=img, caption="📈 Инфографика")
    except Exception as e:
        print("[Ошибка инфографики]", e)

def send_morning_digest():
    if os.path.exists("daily.png"):
        bot.send_photo(chat_id=TELEGRAM_CHANNEL, photo=open("daily.png", "rb"))

    coin_data = requests.get("https://api.coingecko.com/api/v3/coins/markets",
        params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 20, "page": 1}).json()
    prices = "\n".join([
        f"{c['symbol'].upper()} ${c['current_price']} ({c['price_change_percentage_24h']:.1f}%)"
        for c in coin_data
    ])

    msg = f"📊 #Сводка на {datetime.now().strftime('%d.%m.%Y')}\n\n"           f"📈 Топ-20 монет:\n{prices}\n\n"           f"🔓 Разлоки: $ARB ($35M), $IMX ($17M)\n"           f"🎁 Airdrop: zkSync, StarkNet — дедлайны сегодня\n"           f"⚠️ FUD: Binance под давлением SEC\n"           f"🚨 Алерты: SOL +6.3%, BNB –4.2%"

    result = bot.send_message(chat_id=TELEGRAM_CHANNEL, text=msg)
    bot.pin_chat_message(chat_id=TELEGRAM_CHANNEL, message_id=result.message_id, disable_notification=True)
    send_financial_calendar()
    send_infographics()

def needs_translation(text):
    return sum(1 for c in text.lower() if c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя') < 3

def translate_text(text):
    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Переведи на русский заголовок крипто-новости: {text}"}],
            max_tokens=100,
            temperature=0.3
        )
        return res.choices[0].message.content.strip()
    except:
        return text

def send_news(title, link, tag="📰"):
    if is_silent_hours():
        print("[Тихо] Пропущено:", title)
        return False
    if link not in sent_links:
        if needs_translation(title):
            title = translate_text(title)
        msg = f"{tag} <b>{title}</b>\n{link}"
        try:
            bot.send_message(chat_id=TELEGRAM_CHANNEL, text=msg, parse_mode="HTML")
            sent_links.add(link)
            return True
        except Exception as e:
            print("[Ошибка отправки]", e)
    return False

def save_sent():
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent_links), f)

def check_rss():
    updated = False
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                if send_news(entry.title, entry.link, "📰"):
                    updated = True
        except Exception as e:
            print("[RSS ошибка]", url, e)
    return updated

def start_news_loop():
    while True:
        check_rss()
        save_sent()
        time.sleep(CHECK_INTERVAL)

def handle_digest(update, context): send_morning_digest()
def handle_calendar(update, context): send_financial_calendar()
def handle_analytics(update, context): send_infographics()
def handle_news(update, context): check_rss()
def handle_help(update, context):
    help_text = (
        "/сводка – Утренняя сводка"

        "/календарь – Финансовый календарь"
        "/аналитика – Инфокартинки"
        "/новости – Принудительная проверка новостей"
        "/помощь – Список команд"
    )
    context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

RSS_FEEDS = [
    "https://forklog.com/feed", "https://bits.media/rss/news/", "https://ru.ihodl.com/rss/",
    "https://cryptonews.net/ru/news/feed/", " "https://cointelegraph.com/rss"
]

if os.path.exists(SENT_FILE):
    with open(SENT_FILE, "r") as f:
        sent_links = set(json.load(f))
else:
    sent_links = set()

if __name__ == "__main__":
    threading.Thread(target=start_news_loop, daemon=True).start()
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("сводка", handle_digest))
    dp.add_handler(CommandHandler("календарь", handle_calendar))
    dp.add_handler(CommandHandler("аналитика", handle_analytics))
    dp.add_handler(CommandHandler("новости", handle_news))
    dp.add_handler(CommandHandler("помощь", handle_help))

    print("🤖 Бот с командами запущен.")
    updater.start_polling()
    updater.idle()