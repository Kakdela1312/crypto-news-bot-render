from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
import feedparser
import json
import os
import requests
import re
from difflib import SequenceMatcher

import logging
logging.basicConfig(level=logging.INFO)

# === НАСТРОЙКИ через переменные окружения ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHANNEL = os.environ.get("TELEGRAM_CHANNEL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SENT_FILE = "sent_links.json"
CHECK_INTERVAL = 600  # 10 минут

RSS_FEEDS = {
    "https://forklog.com/feed": "ru",
    "https://cryptonews.net/ru/news/feed/": "ru",
    "https://cointelegraph.com/rss": "en",
    "https://www.newsbtc.com/feed/": "en",
    "https://decrypt.co/feed": "en"
}

# Загружаем отправленные ссылки
if os.path.exists(SENT_FILE):
    with open(SENT_FILE, "r") as f:
        sent_links = set(json.load(f))
else:
    sent_links = set()

sent_titles = []

def save_sent():
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent_links), f)

def needs_translation(text):
    return bool(re.search(r'[a-zA-Z]', text))

def translate_text(text):
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": f"Переведи на русский язык заголовок крипто-новости: {text}"}],
            "max_tokens": 100,
            "temperature": 0.3
        }
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        res = resp.json()
        return res["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("[Ошибка перевода]", e)
        return text

def is_similar(title, sent_titles, threshold=0.85):
    for old_title in sent_titles:
        if SequenceMatcher(None, title.lower(), old_title.lower()).ratio() > threshold:
            return True
    return False

def send_news_to_channel(context: CallbackContext):
    global sent_titles
    for url, lang in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                title = entry.title
                link = entry.link
                if link in sent_links or is_similar(title, sent_titles):
                    continue
                if lang == "en" and needs_translation(title):
                    title = translate_text(title)
                msg = f"📰 <b>{title}</b>\n{link}"
                context.bot.send_message(chat_id=TELEGRAM_CHANNEL, text=msg, parse_mode="HTML")
                sent_links.add(link)
                sent_titles.append(title)
                if len(sent_titles) > 50:
                    sent_titles.pop(0)
        except Exception as e:
            print(f"[RSS ошибка] {url}: {e}")
    save_sent()

# === Команды ===
def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Привет! Я публикую свежие крипто-новости в канал.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("/start — запуск\n/help — команды\n/новости — вручную отправить ленты")

def handle_news(update: Update, context: CallbackContext):
    update.message.reply_text("🔄 Проверяю новости...")
    send_news_to_channel(context)
    update.message.reply_text("✅ Новости отправлены.")

def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("новости", handle_news))

    updater.job_queue.run_repeating(send_news_to_channel, interval=CHECK_INTERVAL, first=5)

    print("🤖 Бот с переводом и фильтром запущен.")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
