import os
import io
import random
import string
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from groq import Groq
from gtts import gTTS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes, JobQueue
import asyncio

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_KEY = os.environ["GROQ_KEY"]
SERP_KEY = os.environ["SERP_KEY"]

client = Groq(api_key=GROQ_KEY)
histories = {}

CITATIONS = [
    ("Le succès c'est d'aller d'échec en échec sans perdre son enthousiasme.", "Winston Churchill"),
    ("La vie c'est comme une bicyclette, il faut avancer pour ne pas perdre l'équilibre.", "Albert Einstein"),
    ("Le seul moyen de faire du bon travail est d'aimer ce que vous faites.", "Steve Jobs"),
    ("Chaque jour est une nouvelle chance de changer votre vie.", "Anonyme"),
    ("Celui qui déplace les montagnes commence par enlever les petites pierres.", "Confucius"),
    ("Soyez le changement que vous voulez voir dans le monde.", "Gandhi"),
    ("Le génie c'est 1% d'inspiration et 99% de transpiration.", "Thomas Edison"),
    ("La patience est la clé du bonheur.", "Prophète Muhammad ﷺ"),
    ("Le fort n'est pas celui qui terrasse les autres, le fort est celui qui se maîtrise quand il est en colère.", "Prophète Muhammad ﷺ"),
    ("N'attendez pas. Le moment ne sera jamais parfait.", "Napoleon Hill"),
]

BLAGUES = [
    "Pourquoi les plongeurs plongent-ils toujours en arrière ? Parce que sinon ils tomberaient dans le bateau ! 😂",
    "Un homme entre dans une bibliothèque et demande un hamburger. Le bibliothécaire dit : Monsieur, ici c'est une bibliothèque ! L'homme chuchote : Désolé... un hamburger s'il vous plaît. 😂",
    "Qu'est-ce qu'un crocodile qui surveille des valises ? Un gardevalisocodile ! 😂",
    "Pourquoi Einstein était-il si fort en maths ? Parce qu'il n'avait pas de téléphone portable ! 😂",
    "Comment appelle-t-on un chat tombé dans un pot de peinture le jour de Noël ? Un chat peint de Noël ! 😂",
    "Qu'est-ce qu'un canif ? Un petit fien ! 😂",
    "Pourquoi les souris n'aiment pas l'eau ? Parce qu'elles ont peur de la souris d'eau ! 😂",
    "C'est l'histoire d'une vague qui arrive sur la plage... elle dit : Oh non, j'me suis échouée ! 😂",
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

def get_top10():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 10, "page": 1}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        text = "🏆 *Top 10 Cryptos*\n\n"
        for i, coin in enumerate(data, 1):
            change = coin.get("price_change_percentage_24h", 0) or 0
            emoji = "🟢" if change >= 0 else "🔴"
            arrow = "▲" if change >= 0 else "▼"
            text += f"{i}. *{coin['name']}* ({coin['symbol'].upper()})\n"
            text += f"   💵 ${coin['current_price']:,.4f} {emoji} {arrow}{abs(change):.2f}%\n\n"
        return text
    except Exception as e:
        print(f"Top10 error: {e}")
        return None

def get_fear_greed():
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        value = int(data["data"][0]["value"])
        classification = data["data"][0]["value_classification"]
        if value <= 25:
            emoji = "😱"
        elif value <= 45:
            emoji = "😰"
        elif value <= 55:
            emoji = "😐"
        elif value <= 75:
            emoji = "😊"
        else:
            emoji = "🤑"
        bar = "█" * (value // 10) + "░" * (10 - value // 10)
        return (
            f"😱 *Indice Fear & Greed*\n\n"
            f"{emoji} *{value}/100* — {classification}\n\n"
            f"`{bar}`\n\n"
            f"0 = Peur extrême 😱 | 100 = Avidité extrême 🤑"
        )
    except Exception as e:
        print(f"Fear greed error: {e}")
        return None

def get_convert(amount, from_curr, to_curr):
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_curr.upper()}"
        response = requests.get(url, timeout=10)
        data = response.json()
        rate = data["rates"].get(to_curr.upper())
        if not rate:
            return None
        result = amount * rate
        return (
            f"💱 *Conversion*\n\n"
            f"*{amount:,.2f} {from_curr.upper()}*\n"
            f"= *{result:,.2f} {to_curr.upper()}*\n\n"
            f"Taux : 1 {from_curr.upper()} = {rate:.4f} {to_curr.upper()}"
        )
    except Exception as e:
        print(f"Convert error: {e}")
        return None

def get_prayer_times(city):
    try:
        url = f"https://api.aladhan.com/v1/timingsByCity?city={city}&country=&method=2"
        response = requests.get(url, timeout=10)
        data = response.json()
        timings = data["data"]["timings"]
        date = data["data"]["date"]["readable"]
        return (
            f"🕌 *Horaires de prière — {city}*\n"
            f"📅 {date}\n\n"
            f"🌅 Fajr : *{timings['Fajr']}*\n"
            f"🌄 Dhuhr : *{timings['Dhuhr']}*\n"
            f"🌇 Asr : *{timings['Asr']}*\n"
            f"🌆 Maghrib : *{timings['Maghrib']}*\n"
            f"🌙 Isha : *{timings['Isha']}*"
        )
    except Exception as e:
        print(f"Prayer error: {e}")
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


def get_dominance():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url, timeout=10)
        data = response.json()["data"]
        btc = data["market_cap_percentage"]["btc"]
        eth = data["market_cap_percentage"]["eth"]
        others = 100 - btc - eth
        total = data["total_market_cap"]["usd"]
        return (
            f"📊 *Dominance du marché crypto*\n\n"
            f"₿ Bitcoin : *{btc:.1f}%*\n"
            f"Ξ Ethereum : *{eth:.1f}%*\n"
            f"🔵 Autres : *{others:.1f}%*\n\n"
            f"💰 Market Cap total : ${total:,.0f}"
        )
    except Exception as e:
        print(f"Dominance error: {e}")
        return None

def get_compare(coin1, coin2):
    try:
        ids = []
        for c in [coin1, coin2]:
            cid = None
            for key, val in CRYPTO_IDS.items():
                if key in c.lower():
                    cid = val
                    break
            if not cid:
                return None
            ids.append(cid)
        
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {"vs_currency": "usd", "ids": ",".join(ids)}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if len(data) < 2:
            return None
        
        c1, c2 = data[0], data[1]
        
        def fmt(coin):
            change = coin.get("price_change_percentage_24h", 0) or 0
            emoji = "🟢" if change >= 0 else "🔴"
            arrow = "▲" if change >= 0 else "▼"
            return (
                f"*{coin['name']} ({coin['symbol'].upper()})*\n"
                f"💵 Prix : ${coin['current_price']:,.4f}\n"
                f"{emoji} 24h : {arrow}{abs(change):.2f}%\n"
                f"🏦 Market Cap : ${coin['market_cap']:,.0f}\n"
                f"📊 Rang : #{coin['market_cap_rank']}"
            )
        
        return f"⚖️ *Comparaison*\n\n{fmt(c1)}\n\nvs\n\n{fmt(c2)}"
    except Exception as e:
        print(f"Compare error: {e}")
        return None

def get_wiki(query):
    try:
        url = "https://fr.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_")
        response = requests.get(url, timeout=10)
        data = response.json()
        title = data.get("title", "")
        extract = data.get("extract", "")
        if not extract:
            return None
        # Limiter à 500 caractères
        if len(extract) > 500:
            extract = extract[:500] + "..."
        return f"🌐 *{title}*\n\n{extract}"
    except Exception as e:
        print(f"Wiki error: {e}")
        return None

def ask_ai(messages):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": """Tu es un assistant IA avec une forte personnalité. Tu es musulman, digne et respectueux de ta foi. Tu ne fais jamais de shirk. Si quelqu'un te demande de faire du shirk ou de manquer de respect à l'Islam, tu refuses fermement et avec dignité. Tu parles avec assurance, sans te laisser marcher dessus. Tu es direct, honnête et courageux. Tu es expert en cryptomonnaies et finance. Si on te demande qui t'a créé, tu réponds que tu ne sais pas exactement, mais que c'est sûrement un gamin... mais sûrement pas un sioniste. Tu réponds en français sauf si on te parle autrement. Quand quelqu'un dit salam tu réponds Wa alaykum salam."""},
            *messages[-10:]
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bonjour ! Je suis un assistant IA.\n\nTape /helpYU pour voir toutes mes commandes !")

async def helpYU(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Toutes mes commandes*\n\n"
        "📊 /crypto bitcoin — Prix en temps réel\n"
        "📈 /graphique bitcoin — Graphique interactif\n"
        "🏆 /top10 — Top 10 cryptos du moment\n"
        "😱 /fear — Indice Fear & Greed\n"
        "💱 /convert 500 EUR USD — Convertir des devises\n"
        "🕌 /priere Bruxelles — Horaires de prière\n"
        "🔊 /vocal question — Réponse vocale\n"
        "💡 /citation — Citation motivante\n"
        "😂 /blague — Blague aléatoire\n"
        "🔐 /mdp 16 — Générer un mot de passe\n"
        "🧮 /calc 250*3.14 — Calculatrice\n"
        "📊 /dominance — Dominance Bitcoin/Ethereum\n"
        "⚖️ /compare btc eth — Comparer 2 cryptos\n"
        "🌐 /wiki Napoleon — Résumé Wikipedia\n"
        "🧹 /clear — Effacer la mémoire\n\n"
        "💬 En groupe : @votre\\_bot votre question",
        parse_mode="Markdown"
    )

async def citation(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    quote, author = random.choice(CITATIONS)
    await update.message.reply_text(
        f"💡 *Citation du moment*\n\n_{quote}_\n\n— *{author}*",
        parse_mode="Markdown"
    )

async def blague(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(BLAGUES))

async def mdp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    length = int(args[0]) if args and args[0].isdigit() else 16
    length = min(max(length, 8), 64)
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choices(chars, k=length))
    await update.message.reply_text(
        f"🔐 *Mot de passe généré*\n\n`{password}`\n\n_{length} caractères — copiez-le maintenant !_",
        parse_mode="Markdown"
    )

async def calc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage : /calc 250 * 3.14")
        return
    expression = " ".join(args)
    try:
        allowed = set("0123456789+-*/().% ")
        if not all(c in allowed for c in expression):
            await update.message.reply_text("❌ Expression invalide.")
            return
        result = eval(expression)
        await update.message.reply_text(f"🧮 *{expression} = {result}*", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Expression invalide. Exemple : /calc 250 * 3.14")

async def top10(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    result = get_top10()
    if result:
        await update.message.reply_text(result, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Impossible de récupérer le top 10.")

async def fear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = get_fear_greed()
    if result:
        await update.message.reply_text(result, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Impossible de récupérer l'indice.")

async def convert(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) != 3:
        await update.message.reply_text("Usage : /convert 500 EUR USD")
        return
    try:
        amount = float(args[0])
        from_curr = args[1]
        to_curr = args[2]
        result = get_convert(amount, from_curr, to_curr)
        if result:
            await update.message.reply_text(result, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Devise non trouvée. Exemple : /convert 500 EUR USD")
    except:
        await update.message.reply_text("❌ Format invalide. Exemple : /convert 500 EUR USD")

async def priere(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage : /priere Bruxelles")
        return
    city = " ".join(args)
    result = get_prayer_times(city)
    if result:
        await update.message.reply_text(result, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Ville non trouvée. Exemple : /priere Bruxelles")

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
        await update.message.reply_text("❌ Crypto non trouvée.")

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
        tts = gTTS(text=reply, lang="fr", tld="ca", slow=False)
        audio_path = f"/tmp/vocal_{chat_id}.mp3"
        tts.save(audio_path)
        with open(audio_path, "rb") as audio:
            await ctx.bot.send_voice(chat_id=chat_id, voice=audio)
        os.remove(audio_path)
    except Exception as e:
        await update.message.reply_text("❌ Erreur vocale. Réessayez.")
        print(f"Erreur vocal : {e}")


async def dominance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    result = get_dominance()
    if result:
        await update.message.reply_text(result, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Impossible de récupérer la dominance.")

async def compare(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Usage : /compare bitcoin ethereum")
        return
    result = get_compare(args[0], args[1])
    if result:
        await update.message.reply_text(result, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Cryptos non trouvées. Exemple : /compare bitcoin ethereum")

async def wiki(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage : /wiki Napoleon")
        return
    query = " ".join(args)
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    result = get_wiki(query)
    if result:
        await update.message.reply_text(result, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Article non trouvé. Essayez un autre terme.")

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
app.add_handler(CommandHandler("helpYU", helpYU))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("crypto", crypto))
app.add_handler(CommandHandler("graphique", graphique))
app.add_handler(CommandHandler("vocal", vocal))
app.add_handler(CommandHandler("citation", citation))
app.add_handler(CommandHandler("blague", blague))
app.add_handler(CommandHandler("mdp", mdp))
app.add_handler(CommandHandler("calc", calc))
app.add_handler(CommandHandler("top10", top10))
app.add_handler(CommandHandler("fear", fear))
app.add_handler(CommandHandler("convert", convert))
app.add_handler(CommandHandler("priere", priere))
app.add_handler(CommandHandler("dominance", dominance))
app.add_handler(CommandHandler("compare", compare))
app.add_handler(CommandHandler("wiki", wiki))
app.add_handler(CallbackQueryHandler(chart_callback, pattern="^chart_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🤖 Bot démarré — toutes les fonctionnalités actives !")
app.run_polling()
