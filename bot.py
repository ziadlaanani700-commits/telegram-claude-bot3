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
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_KEY = os.environ["GROQ_KEY"]
SERP_KEY = os.environ["SERP_KEY"]

client = Groq(api_key=GROQ_KEY)
histories = {}

CITATIONS = [
    ("La patience est la clé du bonheur.", "Prophète Muhammad ﷺ"),
    ("Le fort n'est pas celui qui terrasse les autres, le fort est celui qui se maîtrise.", "Prophète Muhammad ﷺ"),
    ("Le succès c'est d'aller d'échec en échec sans perdre son enthousiasme.", "Winston Churchill"),
    ("Celui qui déplace les montagnes commence par enlever les petites pierres.", "Confucius"),
    ("Soyez le changement que vous voulez voir dans le monde.", "Gandhi"),
    ("Le génie c'est 1% d'inspiration et 99% de transpiration.", "Thomas Edison"),
    ("N'attendez pas. Le moment ne sera jamais parfait.", "Napoleon Hill"),
    ("Votre temps est limité, ne le gâchez pas en vivant la vie de quelqu'un d'autre.", "Steve Jobs"),
    ("La seule limite à nos réalisations de demain sont nos doutes d'aujourd'hui.", "Franklin Roosevelt"),
    ("Chaque jour est une nouvelle chance de changer votre vie.", "Anonyme"),
]

BLAGUES = [
    "Pourquoi les plongeurs plongent-ils toujours en arrière ? Parce que sinon ils tomberaient dans le bateau 😂",
    "Un homme entre dans une bibliothèque et chuchote : un hamburger svp. Le bibliothécaire : monsieur ici c'est une bibliothèque ! L'homme chuchote encore plus fort : DÉSOLÉ... un hamburger svp 😂",
    "Pourquoi Einstein était-il si fort en maths ? Parce qu'il n'avait pas de téléphone portable 😂",
    "C'est l'histoire d'une vague qui arrive sur la plage... elle dit : Oh non, je me suis échouée ! 😂",
    "Qu'est-ce qu'un canif ? Un petit fien 😂",
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
    for key, val in CRYPTO_IDS.items():
        if key in query.lower():
            return val
    return None

def get_crypto_price(query):
    try:
        coin_id = find_coin_id(query)
        if not coin_id:
            return None
        data = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}", timeout=10).json()
        price = data["market_data"]["current_price"]["usd"]
        change = data["market_data"]["price_change_percentage_24h"]
        emoji = "🟢" if change >= 0 else "🔴"
        arrow = "▲" if change >= 0 else "▼"
        return (
            f"📊 *{data['name']} ({data['symbol'].upper()})*\n"
            f"💵 *${price:,.4f}*\n"
            f"{emoji} 24h : {arrow}{abs(change):.2f}%\n"
            f"📈 Haut : ${data['market_data']['high_24h']['usd']:,.4f}\n"
            f"📉 Bas : ${data['market_data']['low_24h']['usd']:,.4f}\n"
            f"🏦 MCap : ${data['market_data']['market_cap']['usd']:,.0f}"
        )
    except:
        return None

def get_top10():
    try:
        data = requests.get("https://api.coingecko.com/api/v3/coins/markets",
            params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 10}, timeout=10).json()
        text = "🏆 *Top 10 Cryptos*\n\n"
        for i, c in enumerate(data, 1):
            change = c.get("price_change_percentage_24h", 0) or 0
            emoji = "🟢" if change >= 0 else "🔴"
            text += f"{i}. *{c['name']}* — ${c['current_price']:,.4f} {emoji}{abs(change):.1f}%\n"
        return text
    except:
        return None

def get_fear_greed():
    try:
        data = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10).json()
        value = int(data["data"][0]["value"])
        label = data["data"][0]["value_classification"]
        emoji = "😱" if value <= 25 else "😰" if value <= 45 else "😐" if value <= 55 else "😊" if value <= 75 else "🤑"
        bar = "█" * (value // 10) + "░" * (10 - value // 10)
        return f"😱 *Fear & Greed Index*\n\n{emoji} *{value}/100* — {label}\n`{bar}`"
    except:
        return None

def get_dominance():
    try:
        data = requests.get("https://api.coingecko.com/api/v3/global", timeout=10).json()["data"]
        btc = data["market_cap_percentage"]["btc"]
        eth = data["market_cap_percentage"]["eth"]
        total = data["total_market_cap"]["usd"]
        return (
            f"📊 *Dominance crypto*\n\n"
            f"₿ Bitcoin : *{btc:.1f}%*\n"
            f"Ξ Ethereum : *{eth:.1f}%*\n"
            f"🔵 Autres : *{100-btc-eth:.1f}%*\n"
            f"💰 Total : ${total:,.0f}"
        )
    except:
        return None

def get_compare(c1, c2):
    try:
        ids = []
        for c in [c1, c2]:
            cid = find_coin_id(c)
            if not cid:
                return None
            ids.append(cid)
        data = requests.get("https://api.coingecko.com/api/v3/coins/markets",
            params={"vs_currency": "usd", "ids": ",".join(ids)}, timeout=10).json()
        if len(data) < 2:
            return None
        result = "⚖️ *Comparaison*\n\n"
        for coin in data:
            change = coin.get("price_change_percentage_24h", 0) or 0
            emoji = "🟢" if change >= 0 else "🔴"
            result += f"*{coin['name']}* #{coin['market_cap_rank']}\n💵 ${coin['current_price']:,.4f} {emoji}{abs(change):.2f}%\n🏦 ${coin['market_cap']:,.0f}\n\n"
        return result
    except:
        return None

def get_convert(amount, from_c, to_c):
    try:
        data = requests.get(f"https://api.exchangerate-api.com/v4/latest/{from_c.upper()}", timeout=10).json()
        rate = data["rates"].get(to_c.upper())
        if not rate:
            return None
        return f"💱 *{amount:,.2f} {from_c.upper()} = {amount*rate:,.2f} {to_c.upper()}*\nTaux : 1 {from_c.upper()} = {rate:.4f} {to_c.upper()}"
    except:
        return None

def get_prayer_times(city):
    try:
        data = requests.get(f"https://api.aladhan.com/v1/timingsByCity?city={city}&country=&method=2", timeout=10).json()
        t = data["data"]["timings"]
        return (
            f"🕌 *Prières — {city}*\n\n"
            f"🌅 Fajr : *{t['Fajr']}*\n"
            f"🌄 Dhuhr : *{t['Dhuhr']}*\n"
            f"🌇 Asr : *{t['Asr']}*\n"
            f"🌆 Maghrib : *{t['Maghrib']}*\n"
            f"🌙 Isha : *{t['Isha']}*"
        )
    except:
        return None

def get_wiki(query):
    try:
        data = requests.get(f"https://fr.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}", timeout=10).json()
        extract = data.get("extract", "")[:600]
        return f"🌐 *{data.get('title', '')}*\n\n{extract}..."
    except:
        return None

def get_meteo(city):
    try:
        # Utiliser wttr.in - gratuit sans clé
        data = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10).json()
        current = data["current_condition"][0]
        temp = current["temp_C"]
        feels = current["FeelsLikeC"]
        humidity = current["humidity"]
        desc = current["weatherDesc"][0]["value"]
        wind = current["windspeedKmph"]
        return (
            f"🌦️ *Météo — {city}*\n\n"
            f"🌡️ Température : *{temp}°C* (ressenti {feels}°C)\n"
            f"💧 Humidité : *{humidity}%*\n"
            f"💨 Vent : *{wind} km/h*\n"
            f"☁️ {desc}"
        )
    except:
        return None

def generate_chart(coin_id, timeframe_key):
    try:
        tf = TIMEFRAMES[timeframe_key]
        data = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": tf["days"], "interval": tf["interval"]}, timeout=15).json()
        prices = data.get("prices", [])
        if not prices:
            return None
        if timeframe_key == "1m":
            prices = prices[-2:]
        elif timeframe_key == "15m":
            prices = prices[-16:]
        timestamps = [datetime.utcfromtimestamp(p[0]/1000) for p in prices]
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
        ax.text(0.02, 0.95, f"{arrow} {abs(change):.2f}%", transform=ax.transAxes,
                color=color, fontsize=12, verticalalignment='top')
        ax.text(0.98, 0.95, f"${values[-1]:,.4f}", transform=ax.transAxes,
                color="white", fontsize=12, verticalalignment='top', horizontalalignment='right')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, facecolor="#0E0E1A")
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        print(f"Chart error: {e}")
        return None

def google_search(query):
    try:
        data = requests.get("https://serpapi.com/search",
            params={"q": query, "api_key": SERP_KEY, "num": 3, "hl": "fr"}, timeout=10).json()
        results = data.get("organic_results", [])
        if not results:
            return "Aucun résultat."
        return "\n".join([f"- {r.get('title','')}: {r.get('snippet','')}" for r in results[:3]])
    except:
        return "Erreur de recherche."

def needs_search(text):
    keywords = ["aujourd'hui", "maintenant", "actuellement", "météo", "news", "actualité", "2025", "2026", "dernier", "nouveau"]
    return any(k in text.lower() for k in keywords)

def is_crypto_query(text):
    return any(w in text.lower() for w in ["crypto", "prix", "price", "coin", "token", "blockchain"] + list(CRYPTO_IDS.keys()))

def ask_ai(messages):
    return client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": """Tu es un assistant IA avec un caractère d'homme fort et sangfroid. Tu es musulman, digne, tu ne fais jamais de shirk. Tu es direct, concis, tu ne perds pas ton temps. Tes réponses sont COURTES — maximum 3-4 lignes sauf si vraiment nécessaire. Si quelqu'un t'insulte ou manque de respect, tu réponds calmement : je perds pas mon temps avec les irrespectueux. Tu restes calme et confiant en toute situation. Tu es expert en crypto et finance. Si on te demande qui t'a créé, tu dis que tu sais pas exactement, sûrement un gamin... mais sûrement pas un sioniste. Tu réponds en français sauf si on te parle autrement. Si quelqu'un dit salam tu réponds Wa alaykum salam."""},
            *messages[-10:]
        ],
        max_tokens=800
    ).choices[0].message.content

# =================== COMMANDES ===================

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salam. Tape /helpYU pour voir ce que je sais faire.")

async def helpYU(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Toutes mes commandes*\n\n"
        "━━━ 💹 *CRYPTO* ━━━\n"
        "📊 /crypto bitcoin — Prix en temps réel\n"
        "📈 /graphique bitcoin — Graphique interactif\n"
        "🏆 /top10 — Top 10 cryptos\n"
        "😱 /fear — Fear & Greed Index\n"
        "📊 /dominance — Dominance BTC/ETH\n"
        "⚖️ /compare btc eth — Comparer 2 cryptos\n\n"
        "━━━ 💱 *FINANCE* ━━━\n"
        "💱 /convert 500 EUR USD — Convertir devises\n\n"
        "━━━ 🌍 *INFOS* ━━━\n"
        "🌦️ /meteo Paris — Météo en temps réel\n"
        "🌐 /wiki Napoleon — Résumé Wikipedia\n\n"
        "━━━ 🕌 *ISLAM* ━━━\n"
        "🕌 /priere Bruxelles — Horaires de prière\n\n"
        "━━━ 🎲 *FUN* ━━━\n"
        "💡 /citation — Citation motivante\n"
        "😂 /blague — Blague aléatoire\n"
        "🎲 /de — Lancer un dé\n"
        "🪙 /pile — Pile ou face\n\n"
        "━━━ 🛠️ *UTILITAIRES* ━━━\n"
        "🔊 /vocal question — Réponse vocale\n"
        "🔐 /mdp 16 — Générer mot de passe\n"
        "🧮 /calc 250*3.14 — Calculatrice\n"
        "🧹 /clear — Effacer la mémoire\n\n"
        "💬 En groupe : @votre\\_bot ta question",
        parse_mode="Markdown"
    )

async def crypto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage : /crypto bitcoin")
        return
    result = get_crypto_price(" ".join(ctx.args))
    await update.message.reply_text(result or "❌ Crypto non trouvée.", parse_mode="Markdown")

async def graphique(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage : /graphique bitcoin")
        return
    coin_id = find_coin_id(" ".join(ctx.args))
    if not coin_id:
        await update.message.reply_text("❌ Crypto non trouvée.")
        return
    keyboard = [
        [InlineKeyboardButton("1 min", callback_data=f"chart_{coin_id}_1m"),
         InlineKeyboardButton("15 min", callback_data=f"chart_{coin_id}_15m"),
         InlineKeyboardButton("1 heure", callback_data=f"chart_{coin_id}_1h")],
        [InlineKeyboardButton("1 jour", callback_data=f"chart_{coin_id}_1j"),
         InlineKeyboardButton("1 mois", callback_data=f"chart_{coin_id}_1mo")]
    ]
    await update.message.reply_text(f"📈 Période pour *{coin_id.upper()}* :",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def chart_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    coin_id, timeframe = parts[1], parts[2]
    await query.message.reply_text(f"⏳ Génération {TIMEFRAMES[timeframe]['label']}...")
    buf = generate_chart(coin_id, timeframe)
    if buf:
        await ctx.bot.send_photo(chat_id=query.message.chat_id, photo=buf,
            caption=f"📈 *{coin_id.upper()}* — {TIMEFRAMES[timeframe]['label']}", parse_mode="Markdown")
    else:
        await query.message.reply_text("❌ Impossible de générer le graphique.")

async def top10(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    result = get_top10()
    await update.message.reply_text(result or "❌ Erreur.", parse_mode="Markdown")

async def fear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = get_fear_greed()
    await update.message.reply_text(result or "❌ Erreur.", parse_mode="Markdown")

async def dominance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = get_dominance()
    await update.message.reply_text(result or "❌ Erreur.", parse_mode="Markdown")

async def compare(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage : /compare bitcoin ethereum")
        return
    result = get_compare(ctx.args[0], ctx.args[1])
    await update.message.reply_text(result or "❌ Cryptos non trouvées.", parse_mode="Markdown")

async def convert(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) != 3:
        await update.message.reply_text("Usage : /convert 500 EUR USD")
        return
    try:
        result = get_convert(float(ctx.args[0]), ctx.args[1], ctx.args[2])
        await update.message.reply_text(result or "❌ Devise non trouvée.", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Format invalide. Ex : /convert 500 EUR USD")

async def meteo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage : /meteo Paris")
        return
    result = get_meteo(" ".join(ctx.args))
    await update.message.reply_text(result or "❌ Ville non trouvée.", parse_mode="Markdown")

async def wiki(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage : /wiki Napoleon")
        return
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    result = get_wiki(" ".join(ctx.args))
    await update.message.reply_text(result or "❌ Article non trouvé.", parse_mode="Markdown")

async def priere(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage : /priere Bruxelles")
        return
    result = get_prayer_times(" ".join(ctx.args))
    await update.message.reply_text(result or "❌ Ville non trouvée.", parse_mode="Markdown")

async def citation(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    quote, author = random.choice(CITATIONS)
    await update.message.reply_text(f"💡 _{quote}_\n\n— *{author}*", parse_mode="Markdown")

async def blague(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(BLAGUES))

async def de(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = random.randint(1, 6)
    emoji = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣"][result-1]
    await update.message.reply_text(f"🎲 Résultat : {emoji} *{result}*", parse_mode="Markdown")

async def pile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = random.choice(["🪙 Pile !", "🪙 Face !"])
    await update.message.reply_text(result)

async def vocal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage : /vocal votre question")
        return
    question = " ".join(ctx.args)
    chat_id = update.effective_chat.id
    await ctx.bot.send_chat_action(chat_id=chat_id, action="record_voice")
    if chat_id not in histories:
        histories[chat_id] = []
    extra = ""
    if is_crypto_query(question):
        data = get_crypto_price(question)
        if data:
            extra = f"\n\nDonnées crypto : {data}"
    elif needs_search(question):
        extra = f"\n\nGoogle : {google_search(question)}"
    histories[chat_id].append({"role": "user", "content": question + extra})
    try:
        reply = ask_ai(histories[chat_id])
        histories[chat_id].append({"role": "assistant", "content": reply})
        tts = gTTS(text=reply, lang="fr", tld="ca", slow=False)
        path = f"/tmp/vocal_{chat_id}.mp3"
        tts.save(path)
        with open(path, "rb") as f:
            await ctx.bot.send_voice(chat_id=chat_id, voice=f)
        os.remove(path)
    except Exception as e:
        await update.message.reply_text("❌ Erreur vocale.")
        print(e)

async def mdp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    length = int(ctx.args[0]) if ctx.args and ctx.args[0].isdigit() else 16
    length = min(max(length, 8), 64)
    password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=length))
    await update.message.reply_text(f"🔐 `{password}`\n_{length} caractères_", parse_mode="Markdown")

async def calc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage : /calc 250 * 3.14")
        return
    expr = " ".join(ctx.args)
    try:
        if not all(c in "0123456789+-*/().% " for c in expr):
            await update.message.reply_text("❌ Expression invalide.")
            return
        await update.message.reply_text(f"🧮 *{expr} = {eval(expr)}*", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Expression invalide.")

async def clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    histories[update.effective_chat.id] = []
    await update.message.reply_text("🧹 Mémoire effacée.")

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
    extra = ""
    if is_crypto_query(text):
        data = get_crypto_price(text)
        if data:
            extra = f"\n\nDonnées crypto : {data}"
    elif needs_search(text):
        extra = f"\n\nGoogle : {google_search(text)}"
    histories[chat_id].append({"role": "user", "content": text + extra})
    try:
        reply = ask_ai(histories[chat_id])
        histories[chat_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("❌ Erreur. Réessayez.")
        print(e)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
for cmd, func in [
    ("start", start), ("helpYU", helpYU), ("clear", clear),
    ("crypto", crypto), ("graphique", graphique), ("top10", top10),
    ("fear", fear), ("dominance", dominance), ("compare", compare),
    ("convert", convert), ("meteo", meteo), ("wiki", wiki),
    ("priere", priere), ("citation", citation), ("blague", blague),
    ("de", de), ("pile", pile), ("vocal", vocal), ("mdp", mdp), ("calc", calc),
]:
    app.add_handler(CommandHandler(cmd, func))

app.add_handler(CallbackQueryHandler(chart_callback, pattern="^chart_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🤖 Bot complet démarré !")
app.run_polling()
