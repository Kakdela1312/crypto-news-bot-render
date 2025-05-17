import os
import json
import feedparser
import telegram
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from flask import Flask, request
from openai import OpenAI
import tradingeconomics as te
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# === КОНФИГ ===
TOKEN = "8165550696:AAFTSgRStivlcC0xlFgOiApubOl6VZJkWHk"
CHANNEL = "@AYE_ZHIZN_VORAM1312"
OPENAI_API_KEY = "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"
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
FEEDS = [
    "https://forklog.com/feed",
    "https://cryptonews.net/ru/news/feed/",
    "https://cointelegraph.com/rss",
    "https://www.newsbtc.com/feed/",
    "https://decrypt.co/feed",
    "https://cryptopotato.com/feed/",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://bitcoinist.com/feed/",
    "https://cryptoslate.com/feed/",
    "https://u.today/rss",
    "https://www.investing.com/rss/news_301.rss",
    "https://dailyhodl.com/feed/",
    "https://www.cryptopolitan.com/feed/",
    "https://ambcrypto.com/feed/",
    "https://blockonomi.com/feed/",
    "https://www.blockchain-council.org/feed/",
    "https://news.bitcoin.com/feed/",
    "https://coinjournal.net/feed/",
    "https://finbold.com/feed/",
    "https://www.cryptobriefing.com/feed/",
    "https://cryptonewsz.com/feed/",
    "https://www.ccn.com/feed/",
    "https://www.fxstreet.com/crypto/news/rss",
    "https://www.bitcoininsider.org/rss",
    "https://www.cryptoglobe.com/latest/feed/",
    "https://www.investingcube.com/feed/",
    "https://www.tronweekly.com/feed/",
    "https://nulltx.com/feed/",
    "https://cryptogeek.info/en/news/rss",
    "https://bitcoingarden.org/feed/",
    "https://coincodex.com/rss/",
    "https://coingape.com/feed/",
    "https://cryptodaily.co.uk/feed",
    "https://www.crypto-news.net/feed/",
    "https://tokenhell.com/feed/",
    "https://www.cryptovibes.com/feed/",
    "https://cryptoticker.io/en/feed/",
    "https://coinspeaker.com/feed/",
    "https://www.crypto-news-flash.com/feed/",
    "https://cryptonewsreview.com/feed/",
    "https://bitcoinmagazine.com/.rss/full",
    "https://coincheckup.com/blog/feed/",
    "https://coincentral.com/feed/",
    "https://bitcourier.co.uk/news/rss",
    "https://cryptototem.com/feed/"
]

SENT_FILE = "sent_links.json"

app = Flask(__name__)


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
    return any(k in text.lower() for k in KEYWORDS)


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


def fetch_important_events(period="day"):
    if period == "week":
        return f"#Weekly\n\n📅 Понедельник, {date.today().strftime('%d.%m')}:\n- Разлоки и события недели..."
    else:
        return f"#Daily\n\n📅 Сегодня, {date.today().strftime('%d.%m')}:\n- Важные события дня..."


def send_weekly_crypto_events():
    try:
        text = fetch_important_events("week")
        image_url = "https://example.com/weekly-banner.jpg"
        bot.send_photo(chat_id=CHANNEL, photo=image_url, caption=text, parse_mode="HTML")
    except Exception as e:
        print("Ошибка при отправке недельной сводки:", e)


def send_daily_crypto_events():
    try:
        text = fetch_important_events("day")
        image_url = "https://example.com/daily-banner.jpg"
        bot.send_photo(chat_id=CHANNEL, photo=image_url, caption=text, parse_mode="HTML")
    except Exception as e:
        print("Ошибка при отправке дневной сводки:", e)


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
    return "✅ Bot is alive!"


if __name__ == "__main__":
    bot.set_webhook(f"https://crypto-news-bot-render.onrender.com/{TOKEN}")

    scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Moscow"))
    scheduler.add_job(check_feeds, trigger="interval", minutes=10)
    scheduler.add_job(send_daily_crypto_events, trigger="cron", hour=10, minute=0)
    scheduler.add_job(send_weekly_crypto_events, trigger="cron", day_of_week="mon", hour=10, minute=0)
    scheduler.start()

    check_feeds()

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
