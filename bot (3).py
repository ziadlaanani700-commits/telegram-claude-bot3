import os
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_KEY = os.environ["GROQ_KEY"]

client = Groq(api_key=GROQ_KEY)
histories = {}

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bonjour ! Je suis un assistant IA créé par Ziad Laanani.\n"
        "Posez-moi n'importe quelle question !\n\n"
        "Dans un groupe, mentionnez-moi avec @nom_du_bot pour m'interpeller."
    )

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

    histories[chat_id].append({"role": "user", "content": text})

    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es un assistant IA intelligent, bienveillant et précis. Tu as été créé par Ziad Laanani. Si quelqu'un te demande qui t'a créé ou qui est ton créateur, tu réponds que c'est Ziad Laanani. Tu réponds en français sauf si on te parle dans une autre langue. Sois concis et utile."},
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
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🤖 Bot démarré avec Groq !")
app.run_polling()
