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
import re

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

RUSSIAN_FEEDS = [
    "https://forklog.com/feed",
    "https://bits.media/rss/news/",
    "https://ru.ihodl.com/rss/",
    "https://cryptonews.net/ru/news/feed/",
    "https://coinjournal.net/ru/news/feed/",
    "https://ru.cointelegraph.com/rss",
    "https://bitnovosti.com/feed/",
    "https://beincrypto.ru/feed/",
    "https://ru.investing.com/rss/news_301.rss",
    "https://banki.ru/news/feed/",
    "https://www.finanz.ru/rss",
    "https://www.vedomosti.ru/rss/news",
    "https://www.rbc.ru/rss/newsline.xml",
    "https://tass.ru/rss/v2.xml",
    "https://cryptorating.ru/rss",
    "https://www.crypto-ratings.ru/rss",
    "https://tjournal.ru/rss/crypto",
    "https://www.cnews.ru/tools/rss/cryptocurrency.xml",
    "https://vc.ru/rss/tags/crypto",
    "https://finam.ru/rss/news/crypto.xml",
    "https://www.banki.ru/news/rss/",
    "https://www.finversia.ru/rss",
    "https://www.kommersant.ru/RSS/news.xml",
    "https://www.rbc.ru/rss/crypto.xml",
    "https://www.forbes.ru/rss",
    "https://www.vedomosti.ru/rss/crypto",
    "https://www.interfax.ru/rss/crypto"
]

RSS_FEEDS = RUSSIAN_FEEDS + [
    "https://cointelegraph.com/rss",
    "https://www.newsbtc.com/feed/",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://decrypt.co/feed",
    "https://www.theblock.co/feeds/rss",
    "https://cryptopotato.com/feed/",
    "https://cryptoslate.com/feed/",
    "https://coinspot.io/feed",
]

CRYPTO_KEYWORDS = [
    "крипто", "биткоин", "bitcoin", "эфириум", "ethereum", "blockchain", "децентрализованный", 
    "defi", "nft", "токен", "майнинг", "биткоин-etf", "кошелёк", "блокчейн", "coin", "crypto", 
    "staking", "exchange", "solana", "binance", "bnb", "decentralized", "btc", "eth", "doge", "ada",
    "ripple", "polkadot", "solidity", "dex", "layer 2", "tokenomics", "airdrops", "web3", "metaverse",
    "hashrate", "fork", "smart contract", "wallet", "ledger", "cryptocurrency"
]

def is_silent_hours():
    h = datetime.now().hour
    return h >= 22 or h < 9

def needs_translation(text):
    # Если есть латинские буквы, считаем нужным перевод
    return bool(re.search(r'[a-zA-Z]', text))

def contains_crypto_keyword(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in CRYPTO_KEYWORDS)

def translate_text(text):
    try:
        print(f"[Запрос на перевод] {text}")
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Переведи на русский заголовок крипто-новости: {text}"}],
            max_tokens=100,
            temperature=0.3
        )
        translated = res.choices[0].message.content.strip()
        print(f"[Переведено] {translated}")
        return translated
    except Exception as e:
        print("[Ошибка перевода]", e)
        return text

def send_news(title, link, source_url, tag="📰"):
    if is_silent_hours():
        print("[Тихо] Пропущено:", title)
        return False
    if not contains_crypto_keyword(title):
        print("[Фильтр] Пропущено (нет ключевых слов):", title)
        return False
    if link not in sent_links:
        try:
            if source_url not in RUSSIAN_FEEDS:
                if needs_translation(title):
                    print(f"[Перевод заголовка] {title}")
                    title = translate_text(title)
            msg = f"{tag} <b>{title}</b>\n{link}"
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
                if send_news(entry.title, entry.link, url, "📰"):
                    updated = True
        except Exception as e:
            print("[RSS ошибка]", url, e)
    return updated

def start_news_loop():
    while True:
        check_rss()
        save_sent()
        time.sleep(CHECK_INTERVAL)

def handle_digest(update, context): 
    pass
def handle_calendar(update, context): 
    pass
def handle_analytics(update, context): 
    pass
def handle_news(update, context): 
    check_rss()
def handle_help(update, context):
    help_text = (
        "/digest – Утренняя сводка\n"
        "/calendar – Финансовый календарь\n"
        "/analytics – Инфокартинки\n"
        "/news – Принудительная проверка новостей\n"
        "/help – Список команд"
    )
    context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

if os.path.exists(SENT_FILE):
    with open(SENT_FILE, "r") as f:
        sent_links = set(json.load(f))
else:
    sent_links = set()

if __name__ == "__main__":
    threading.Thread(target=start_news_loop, daemon=True).start()
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("digest", handle_digest))
    dp.add_handler(CommandHandler("calendar", handle_calendar))
    dp.add_handler(CommandHandler("analytics", handle_analytics))
    dp.add_handler(CommandHandler("news", handle_news))
    dp.add_handler(CommandHandler("help", handle_help))

    print("🤖 Бот с улучшенным переводом запущен.")
    updater.start_polling()
    updater.idle()
