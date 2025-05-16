import os
import json
import time
import feedparser
import telegram
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import openai
import tradingeconomics as te
from telegram.ext import Updater, CommandHandler

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = "8106822791:AAFpNW8FHJZOmJ8HwCgBHeC9gQ5NOnvAdLc"
TELEGRAM_CHANNEL = "@AYE_ZHIZN_VORAM1312"
OPENAI_API_KEY = "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"
TE_API_KEY = "300d469a2fe04f2:7vk6trdkoxhwpak"

CHECK_INTERVAL = 600
SENT_FILE = "sent_combined_news.json"

bot = telegram.Bot(token=TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY
te.login(TE_API_KEY)

# Ключевые слова для фильтрации новостей
KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "binance", "airdrop",
    "token", "altcoin", "dex", "defi", "nft", "wallet", "solana", "sol",
    "cardano", "ada", "polygon", "matic", "etf", "mining", "staking", "exchange"
]

# Список RSS-источников
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

def needs_translation(text):
    return sum(1 for c in text.lower() if c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя') < 3

def translate_text(text):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Переведи на русский: {text}"}],
            max_tokens=100,
            temperature=0.3
        )
        return res['choices'][0]['message']['content'].strip()
    except Exception as e:
        print("[Ошибка GPT перевода]", e)
        return text

def contains_keywords(text):
    return any(k.lower() in text.lower() for k in KEYWORDS)

def send_news(title, link):
    if not contains_keywords(title):
        return False
    if is_silent_hours():
        print("[Тихое время] Пропущено:", title)
        return False
    if needs_translation(title):
        title = translate_text(title)
    msg = f"📰 <b>{title}</b>\n{link}"
    try:
        bot.send_message(chat_id=TELEGRAM_CHANNEL, text=msg, parse_mode="HTML")
        return True
    except Exception as e:
        print("[Ошибка отправки]", e)
    return False

def save_sent(sent_links):
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent_links), f)

def check_rss(sent_links):
    updated = False
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                if entry.link not in sent_links:
                    if send_news(entry.title, entry.link):
                        sent_links.add(entry.link)
                        updated = True
        except Exception as e:
            print("[Ошибка RSS]", url, e)
    if updated:
        save_sent(sent_links)

# Обработчики команд Telegram
def handle_help(update, context):
    update.message.reply_text(
        "/help – список команд\n"
        "/news – вручную получить новости"
    )

def handle_news(update, context):
    check_rss(sent_links)

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

    # фоновая проверка каждые 10 минут
    while True:
        check_rss(sent_links)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
