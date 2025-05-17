import os
import json
import time
import feedparser
import telegram
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from openai import OpenAI
import tradingeconomics as te
from telegram.ext import Updater, CommandHandler

# === КОНФИГ ===
TELEGRAM_TOKEN = "8165550696:AAFTSgRStivlcC0xlFgOiApubOl6VZJkWHk"
TELEGRAM_CHANNEL = "@AYE_ZHIZN_VORAM1312"
OPENAI_API_KEY = "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"
TE_API_KEY = "300d469a2fe04f2:7vk6trdkoxhwpak"
SENT_FILE = "sent_combined_news.json"
CHECK_INTERVAL = 600

# === ИНИЦИАЛИЗАЦИЯ ===
bot = telegram.Bot(token=TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
te.login(TE_API_KEY)

# === СЛОВА ===
KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "binance", "airdrop",
    "token", "altcoin", "dex", "defi", "nft", "wallet", "solana", "sol",
    "cardano", "ada", "polygon", "matic", "layer2", "staking", "airdrops"
]

RSS_FEEDS = [
    "https://forklog.com/feed",
    "https://cryptonews.net/ru/news/feed/",
    "https://cointelegraph.com/rss",
    "https://www.newsbtc.com/feed/",
    "https://decrypt.co/feed",
    "https://cryptopotato.com/feed/",
    "https://www.coindesk.com/arc/outboundfeeds/rss/"
]

def is_silent_hours():
    h = datetime.now().hour
    return h >= 23 or h < 7

def is_russian(text):
    return any(c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for c in text.lower())

def contains_keywords(text):
    return any(k.lower() in text.lower() for k in KEYWORDS)

def translate_text(text):
    try:
        print(f"🔁 Перевод заголовка: {text}")
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Переведи на русский заголовок крипто-новости: {text}"}],
            max_tokens=60,
            temperature=0.3
        )
        translation = res.choices[0].message.content.strip()
        print(f"✅ Переведено: {translation}")
        return translation
    except Exception as e:
        print("❌ Ошибка перевода:", e)
        return text

def send_news(title, link):
    if not contains_keywords(title):
        return False
    if is_silent_hours():
        return False
    if not is_russian(title):
        title = translate_text(title)

    msg = f"📰 <b>{title}</b>\n{link}"
    try:
        print(f"📨 Отправка: {msg}")
        bot.send_message(chat_id=TELEGRAM_CHANNEL, text=msg, parse_mode="HTML")
        return True
    except Exception as e:
        print("❌ Ошибка отправки:", e)
    return False

def save_sent(sent_links):
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent_links), f)

def check_rss(sent_links):
    updated = False
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                if entry.link not in sent_links:
                    if send_news(entry.title, entry.link):
                        sent_links.add(entry.link)
                        updated = True
        except Exception as e:
            print(f"❌ Ошибка RSS: {url}", e)
    if updated:
        save_sent(sent_links)

def handle_help(update, context):
    update.message.reply_text("/help – список команд\n/news – ручная проверка новостей")

def handle_news(update, context):
    check_rss(sent_links)
    update.message.reply_text("✅ Новости проверены вручную.")

def main():
    global sent_links
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            sent_links = set(json.load(f))
    else:
        sent_links = set()

    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("help", handle_help))
    dp.add_handler(CommandHandler("news", handle_news))

    print("✅ Бот запущен.")
    updater.start_polling()

    while True:
        check_rss(sent_links)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
