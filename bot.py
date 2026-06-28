import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8716311827:AAHemWBB9X8srTr8pqmaHz4Zhj1F_T7exVA"
WEB_APP_URL = "https://project-nv8gi.vercel.app/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton(
            text="🚀 Открыть Starlink VPN",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Привет! Добро пожаловать в *Starlink VPN*\n\n"
        "🌐 Быстрый, надёжный и безопасный VPN\n"
        "⭐️ Пробный период всего за 1 ₽\n\n"
        "Нажми кнопку ниже чтобы выбрать тариф и подключиться:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Starlink VPN — помощь*\n\n"
        "/start — главное меню\n"
        "/help — эта справка\n\n"
        "По всем вопросам: @support",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    print("Бот запущен...")
    app.run_polling()
