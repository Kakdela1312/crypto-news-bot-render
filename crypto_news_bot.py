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

# Добавим планировщик для утренней и понедельничной сводки
scheduler = BackgroundScheduler(timezone=pytz.utc)

# функция для утренней сводки
def send_daily_digest():
    today = date.today().strftime("%d.%m.%Y")
    msg = f"🗓️ <b>Важное на день ({today}):</b>\n- Подробности обновятся позже..."
    image_path = "daily.png"
    try:
        with open(image_path, "rb") as img:
            bot.send_photo(chat_id=CHANNEL, photo=img, caption=msg, parse_mode="HTML")
    except Exception as e:
        print("❌ Ошибка при отправке дневной сводки:", e)

# функция для понедельничной сводки
def send_weekly_digest():
    today = date.today().strftime("%d.%m.%Y")
    msg = f"📅 <b>Важное на неделю ({today}):</b>\n- Подробности обновятся позже..."
    image_path = "weekly.png"
    try:
        with open(image_path, "rb") as img:
            bot.send_photo(chat_id=CHANNEL, photo=img, caption=msg, parse_mode="HTML")
    except Exception as e:
        print("❌ Ошибка при отправке недельной сводки:", e)

# расписание задач
scheduler.add_job(send_daily_digest, trigger='cron', hour=7, minute=0)
scheduler.add_job(send_weekly_digest, trigger='cron', day_of_week='mon', hour=7, minute=30)
scheduler.start()
