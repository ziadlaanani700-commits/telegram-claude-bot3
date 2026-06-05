import os
import requests
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_KEY = os.environ["GROQ_KEY"]
SERP_KEY = os.environ["SERP_KEY"]

client = Groq(api_key=GROQ_KEY)
histories = {}

CRYPTO_IDS = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana", "sol": "solana",
    "binance": "binancecoin", "bnb": "binancecoin",
    "xrp": "ripple", "ripple": "ripple",
    "cardano": "cardano", "ada": "cardano",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "avalanche": "avalanche-2", "avax": "avalanche-2",
    "polkadot": "polkadot", "dot": "polkadot",
    "shiba": "shiba-inu", "shib": "shiba-inu",
    "tron": "tron", "trx": "tron",
    "chainlink": "chainlink", "link": "chainlink",
    "polygon": "matic-network", "matic": "matic-network",
    "pepe": "pepe", "ton": "the-open-network",
    "usdt": "tether", "usdc": "usd-coin",
}

def get_crypto_price(query):
    try:
        query_lower = query.lower()
        coin_id = None
        for key, val in CRYPTO_IDS.items():
            if key in query_lower:
                coin_id = val
                break

        if not coin_id:
            return None

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        response = requests.get(url, timeout=10)
        data = response.json()

        name = data["name"]
        symbol = data["symbol"].upper()
        price = data["market_data"]["current_price"]["usd"]
        change_24h = data["market_data"]["price_change_percentage_24h"]
        market_cap = data["market_data"]["market_cap"]["usd"]
        high_24h = data["market_data"]["high_24h"]["usd"]
        low_24h = data["market_data"]["low_24h"]["usd"]

        emoji = "🟢" if change_24h >= 0 else "🔴"
        arrow = "▲" if change_24h >= 0 else "▼"

        return (
            f"📊 *{name} ({symbol})*\n"
            f"💵 Prix : *${price:,.4f}*\n"
            f"{emoji} 24h : *{arrow} {abs(change_24h):.2f}%*\n"
            f"📈 Haut 24h : ${high_24h:,.4f}\n"
            f"📉 Bas 24h : ${low_24h:,.4f}\n"
            f"🏦 Market Cap : ${market_cap:,.0f}"
        )
    except Exception as e:
        return None

def google_search(query):
    try:
        response = requests.get("https://serpapi.com/search", params={
            "q": query,
            "api_key": SERP_KEY,
            "num": 3,
            "hl": "fr"
        }, timeout=10)
        data = response.json()
        results = data.get("organic_results", [])
        if not results:
            return "Aucun résultat trouvé."
        summary = ""
        for r in results[:3]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            summary += f"- {title}: {snippet}\n"
        return summary
    except Exception as e:
        return f"Erreur de recherche: {e}"

def needs_search(text):
    keywords = [
        "aujourd'hui", "maintenant", "actuellement", "récent",
        "météo", "score", "résultat", "news", "actualité",
        "2024", "2025", "2026", "dernier", "nouveau", "nouvelle"
    ]
    text_lower = text.lower()
    return any(k in text_lower for k in keywords)

def is_crypto_query(text):
    text_lower = text.lower()
    crypto_words = ["crypto", "prix", "price", "coin", "token", "wallet", "blockchain"] + list(CRYPTO_IDS.keys())
    return any(w in text_lower for w in crypto_words)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bonjour ! Je suis un assistant IA créé par Ziad Laanani.\n\n"
        "Je peux :\n"
        "📊 Analyser les cryptomonnaies en temps réel\n"
        "🔍 Faire des recherches Google\n"
        "💬 Répondre à toutes vos questions\n\n"
        "Dans un groupe, mentionnez-moi avec @nom_du_bot !"
    )

async def crypto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage : /crypto bitcoin")
        return
    query = " ".join(args)
    result = get_crypto_price(query)
    if result:
        await update.message.reply_text(result, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Crypto non trouvée. Essayez : bitcoin, ethereum, solana...")

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if update.effective_chat.type in ["group", "supergroup"]:
        bot_username = (await ctx.bot.get_me()).username
        if f"@{bot_username}" not in text:
            return
        text = text.replace(f"@{bot_username}", "").strip()

    if not text:
        return

    if chat_id not in histories:
        histories[chat_id] = []

    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")

    extra_context = ""

    if is_crypto_query(text):
        crypto_data = get_crypto_price(text)
        if crypto_data:
            extra_context = f"\n\nDonnées crypto en temps réel :\n{crypto_data}"

    elif needs_search(text):
        search_results = google_search(text)
        extra_context = f"\n\nRésultats Google :\n{search_results}"

    histories[chat_id].append({"role": "user", "content": text + extra_context})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es un assistant IA intelligent créé par Ziad Laanani. Tu es expert en cryptomonnaies et finance. Si on te demande qui t'a créé, tu réponds Ziad Laanani. Tu analyses les données crypto fournies et donnes des insights pertinents. Tu réponds en français sauf si on te parle autrement. Sois précis et utile."},
                *histories[chat_id][-10:]
            ],
            max_tokens=1000
        )
        reply = response.choices[0].message.content
        histories[chat_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text("❌ Une erreur est survenue. Réessayez dans un instant.")
        print(f"Erreur : {e}")

async def clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    histories[chat_id] = []
    await update.message.reply_text("🧹 Mémoire effacée ! Nouvelle conversation.")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("crypto", crypto))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🤖 Bot démarré avec Groq + Crypto + Google Search !")
app.run_polling()
