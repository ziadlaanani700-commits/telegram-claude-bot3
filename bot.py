import os
import io
import random
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from groq import Groq
from gtts import gTTS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_KEY = os.environ["GROQ_KEY"]
SERP_KEY = os.environ["SERP_KEY"]

client = Groq(api_key=GROQ_KEY)
histories = {}

CITATIONS = [
    ("Le succès c'est d'aller d'échec en échec sans perdre son enthousiasme.", "Winston Churchill"),
    ("La vie c'est comme une bicyclette, il faut avancer pour ne pas perdre l'équilibre.", "Albert Einstein"),
    ("Le seul moyen de faire du bon travail est d'aimer ce que vous faites.", "Steve Jobs"),
    ("Croyez en vos rêves et ils se réaliseront peut-être. Croyez en vous et ils se réaliseront sûrement.", "Martin Luther King"),
    ("Le courage c'est de chercher la vérité et de la dire.", "Jean Jaurès"),
    ("Chaque jour est une nouvelle chance de changer votre vie.", "Anonyme"),
    ("La persévérance est la clé du succès.", "Anonyme"),
    ("Ce n'est pas la force mais la détermination qui prime.", "Anonyme"),
    ("Celui qui déplace les montagnes commence par enlever les petites pierres.", "Confucius"),
    ("La seule limite à nos réalisations de demain sont nos doutes d'aujourd'hui.", "Franklin Roosevelt"),
    ("Soyez le changement que vous voulez voir dans le monde.", "Gandhi"),
    ("La vie est ce que vous en faites.", "Anonyme"),
    ("Agis bien, et ne te soucie pas du reste.", "Anonyme"),
    ("Il faut toujours viser la lune, car même en cas d'échec, on atterrit dans les étoiles.", "Oscar Wilde"),
    ("Le génie c'est 1% d'inspiration et 99% de transpiration.", "Thomas Edison"),
    ("Votre temps est limité, ne le gâchez pas en vivant la vie de quelqu'un d'autre.", "Steve Jobs"),
    ("Le plus grand risque est de ne prendre aucun risque.", "Mark Zuckerberg"),
    ("Tout ce que l'esprit peut concevoir et croire, il peut l'atteindre.", "Napoleon Hill"),
    ("Le bonheur n'est pas quelque chose de prêt à l'emploi. Il vient de vos propres actions.", "Dalaï Lama"),
    ("N'attendez pas. Le moment ne sera jamais parfait.", "Napoleon Hill"),
]

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

TIMEFRAMES = {
    "1m":  {"days": "1",  "interval": "minutely", "label": "1 Minute"},
    "15m": {"days": "1",  "interval": "minutely", "label": "15 Minutes"},
    "1h":  {"days": "1",  "interval": "hourly",   "label": "1 Heure"},
    "1j":  {"days": "1",  "interval": "hourly",   "label": "1 Jour"},
    "1mo": {"days": "30", "interval": "daily",    "label": "1 Mois"},
}

def find_coin_id(query):
    query_lower = query.lower().strip()
    for key, val in CRYPTO_IDS.items():
        if key in query_lower:
            return val
    return None

def get_crypto_price(query):
    try:
        coin_id = find_coin_id(query)
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
    except:
        return None

def generate_chart(coin_id, timeframe_key):
    try:
        tf = TIMEFRAMES[timeframe_key]
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": tf["days"], "interval": tf["interval"]}
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        prices = data.get("prices", [])
        if not prices:
            return None
        if timeframe_key == "1m":
            prices = prices[-2:]
        elif timeframe_key == "15m":
            prices = prices[-16:]
        timestamps = [datetime.utcfromtimestamp(p[0] / 1000) for p in prices]
        values = [p[1] for p in prices]
        color = "#00C896" if values[-1] >= values[0] else "#FF4B6E"
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor("#0E0E1A")
        ax.set_facecolor("#0E0E1A")
        ax.plot(timestamps, values, color=color, linewidth=2)
        ax.fill_between(timestamps, values, alpha=0.15, color=color)
        ax.set_title(f"{coin_id.upper()} — {tf['label']}", color="white", fontsize=14, pad=15)
        ax.tick_params(colors="gray")
        for spine in ax.spines.values():
            spine.set_edgecolor("#2A2A3E")
        ax.grid(color="#2A2A3E", linestyle="--", linewidth=0.5)
        change = ((values[-1] - values[0]) / values[0]) * 100
        arrow = "▲" if change >= 0 else "▼"
        change_color = "#00C896" if change >= 0 else "#FF4B6E"
        ax.text(0.02, 0.95, f"{arrow} {abs(change):.2f}%", transform=ax.transAxes,
                color=change_color, fontsize=12, verticalalignment='top')
        ax.text(0.98, 0.95, f"${values[-1]:,.4f}", transform=ax.transAxes,
                color="white", fontsize=12, verticalalignment='top', horizontalalignment='right')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, facecolor="#0E0E1A")
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        print(f"Erreur graphique: {e}")
        return None

def google_search(query):
    try:
        response = requests.get("https://serpapi.com/search", params={
            "q": query, "api_key": SERP_KEY, "num": 3, "hl": "fr"
        }, timeout=10)
        data = response.json()
        results = data.get("organic_results", [])
        if not results:
            return "Aucun résultat trouvé."
        summary = ""
        for r in results[:3]:
            summary += f"- {r.get('title', '')}: {r.get('snippet', '')}\n"
        return summary
    except:
        return "Erreur de recherche."

def needs_search(text):
    keywords = ["aujourd'hui", "maintenant", "actuellement", "météo", "news",
                "actualité", "2024", "2025", "2026", "dernier", "nouveau"]
    return any(k in text.lower() for k in keywords)

def is_crypto_query(text):
    crypto_words = ["crypto", "prix", "price", "coin", "token", "blockchain"] + list(CRYPTO_IDS.keys())
    return any(w in text.lower() for w in crypto_words)

def ask_ai(messages):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Tu es un assistant IA intelligent créé par Ziad Laanani. Tu es expert en cryptomonnaies et finance. Si on te demande qui t'a créé, tu réponds Ziad Laanani. Tu réponds en français sauf si on te parle autrement. Sois précis et utile."},
            *messages[-10:]
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bonjour ! Je suis un assistant IA créé par Ziad Laanani.\n\n"
        "Mes commandes :\n"
        "📊 /crypto bitcoin — Prix en temps réel\n"
        "📈 /graphique bitcoin — Graphique interactif\n"
        "🔊 /vocal votre question — Réponse vocale\n"
        "💡 /citation — Citation motivante\n"
        "🧹 /clear — Effacer la mémoire\n\n"
        "Dans un groupe, mentionnez-moi avec @nom_du_bot !"
    )

async def citation(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    quote, author = random.choice(CITATIONS)
    await update.message.reply_text(
        f"💡 *Citation du moment*\n\n"
        f"_{quote}_\n\n"
        f"— *{author}*",
        parse_mode="Markdown"
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

async def graphique(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage : /graphique bitcoin")
        return
    query = " ".join(args)
    coin_id = find_coin_id(query)
    if not coin_id:
        await update.message.reply_text("❌ Crypto non trouvée.")
        return
    keyboard = [
        [
            InlineKeyboardButton("1 min", callback_data=f"chart_{coin_id}_1m"),
            InlineKeyboardButton("15 min", callback_data=f"chart_{coin_id}_15m"),
            InlineKeyboardButton("1 heure", callback_data=f"chart_{coin_id}_1h"),
        ],
        [
            InlineKeyboardButton("1 jour", callback_data=f"chart_{coin_id}_1j"),
            InlineKeyboardButton("1 mois", callback_data=f"chart_{coin_id}_1mo"),
        ]
    ]
    await update.message.reply_text(
        f"📈 Choisissez la période pour *{coin_id.upper()}* :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def chart_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    coin_id = parts[1]
    timeframe = parts[2]
    label = TIMEFRAMES[timeframe]["label"]
    await query.message.reply_text(f"⏳ Génération du graphique {label}...")
    buf = generate_chart(coin_id, timeframe)
    if buf:
        await ctx.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=buf,
            caption=f"📈 *{coin_id.upper()}* — {label}",
            parse_mode="Markdown"
        )
    else:
        await query.message.reply_text("❌ Impossible de générer le graphique.")

async def vocal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage : /vocal votre question ici")
        return
    question = " ".join(args)
    chat_id = update.effective_chat.id
    await ctx.bot.send_chat_action(chat_id=chat_id, action="record_voice")
    if chat_id not in histories:
        histories[chat_id] = []
    extra_context = ""
    if is_crypto_query(question):
        crypto_data = get_crypto_price(question)
        if crypto_data:
            extra_context = f"\n\nDonnées crypto : {crypto_data}"
    elif needs_search(question):
        extra_context = f"\n\nRésultats Google :\n{google_search(question)}"
    histories[chat_id].append({"role": "user", "content": question + extra_context})
    try:
        reply = ask_ai(histories[chat_id])
        histories[chat_id].append({"role": "assistant", "content": reply})
        tts = gTTS(text=reply, lang="fr", tld="fr")
        audio_path = f"/tmp/vocal_{chat_id}.mp3"
        tts.save(audio_path)
        with open(audio_path, "rb") as audio:
            await ctx.bot.send_voice(chat_id=chat_id, voice=audio)
        os.remove(audio_path)
    except Exception as e:
        await update.message.reply_text("❌ Erreur vocale. Réessayez.")
        print(f"Erreur vocal : {e}")

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
            extra_context = f"\n\nDonnées crypto : {crypto_data}"
    elif needs_search(text):
        extra_context = f"\n\nRésultats Google :\n{google_search(text)}"
    histories[chat_id].append({"role": "user", "content": text + extra_context})
    try:
        reply = ask_ai(histories[chat_id])
        histories[chat_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("❌ Une erreur est survenue. Réessayez.")
        print(f"Erreur : {e}")

async def clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    histories[chat_id] = []
    await update.message.reply_text("🧹 Mémoire effacée !")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("crypto", crypto))
app.add_handler(CommandHandler("graphique", graphique))
app.add_handler(CommandHandler("vocal", vocal))
app.add_handler(CommandHandler("citation", citation))
app.add_handler(CallbackQueryHandler(chart_callback, pattern="^chart_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🤖 Bot démarré avec Groq + Crypto + Graphiques + Vocal + Citations !")
app.run_polling()
