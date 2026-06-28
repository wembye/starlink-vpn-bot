import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, LabeledPrice
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = "8716311827:AAHemWBB9X8srTr8pqmaHz4Zhj1F_T7exVA"
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://project-nv8gi.vercel.app/")

# Stars prices (1 Star = ~0.013 USD, примерно)
PLANS = {
    "trial":   {"stars": 1,   "label": "Пробный период (8 часов)", "days": 0},
    "month":   {"stars": 200, "label": "1 месяц",                  "days": 30},
    "quarter": {"stars": 500, "label": "3 месяца",                 "days": 90},
    "year":    {"stars": 1600,"label": "1 год",                    "days": 365},
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = user.first_name or ""
    username = f"@{user.username}" if user.username else first_name

    # Pass user info to Mini App via URL hash
    user_data = f"id={user.id}&name={username}&first={first_name}"
    import urllib.parse
    encoded = urllib.parse.quote(user_data)
    webapp_url = f"{WEB_APP_URL}?user={encoded}"

    keyboard = [[
        InlineKeyboardButton(
            text="🚀 Открыть Starlink VPN",
            web_app=WebAppInfo(url=webapp_url)
        )
    ]]

    await update.message.reply_text(
        f"👋 Привет, {first_name}!\n\n"
        f"*Starlink VPN* — быстрый и безопасный VPN\n\n"
        f"⭐ Пробный период за 1 Star\n"
        f"🌐 Безлимит устройств · Без логов\n"
        f"🔒 WireGuard протокол\n\n"
        f"Нажми кнопку чтобы выбрать тариф:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать инлайн кнопки выбора тарифа"""
    keyboard = []
    for plan_id, plan in PLANS.items():
        keyboard.append([InlineKeyboardButton(
            text=f"{plan['label']} — {plan['stars']} ⭐",
            callback_data=f"buy_{plan_id}"
        )])
    await update.message.reply_text(
        "💳 *Выберите тариф:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("buy_"):
        plan_id = query.data.replace("buy_", "")
        plan = PLANS.get(plan_id)
        if not plan:
            return

        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=f"Starlink VPN — {plan['label']}",
            description=f"VPN подписка: {plan['label']}. WireGuard, безлимит устройств, без логов.",
            payload=f"vpn_{plan_id}_{query.from_user.id}",
            currency="XTR",  # Telegram Stars
            prices=[LabeledPrice(label=plan['label'], amount=plan['stars'])],
            provider_token="",  # Пустой для Stars
        )

async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем данные из Mini App когда пользователь нажимает оплатить"""
    data = update.effective_message.web_app_data.data
    user = update.effective_user

    import json
    try:
        payload = json.loads(data)
        plan_id = payload.get("plan")
        plan = PLANS.get(plan_id)
        if not plan:
            return

        keyboard = [[InlineKeyboardButton(
            text=f"Оплатить {plan['stars']} ⭐",
            callback_data=f"buy_{plan_id}"
        )]]

        await update.message.reply_text(
            f"💳 *{plan['label']}* — {plan['stars']} Stars\n\n"
            f"Нажми кнопку для оплаты через Telegram Stars:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"webapp_data error: {e}")

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждаем оплату"""
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """После успешной оплаты — отправляем VPN ключ"""
    payment = update.message.successful_payment
    payload = payment.invoice_payload  # vpn_month_123456

    parts = payload.split("_")
    plan_id = parts[1] if len(parts) > 1 else "month"
    plan = PLANS.get(plan_id, PLANS["month"])

    # Здесь в реальном боте: генерируй реальный WireGuard ключ
    vpn_config = """[Interface]
PrivateKey = wOEI9rqqbDwnN8/BdXXXXXXXXXX=
Address = 10.66.66.2/32
DNS = 1.1.1.1

[Peer]
PublicKey = JRI8Xc0zKP9kXk8qPXXXXXXXXXX=
Endpoint = vpn.starlink.io:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25"""

    await update.message.reply_text(
        f"✅ *Оплата прошла! Спасибо!*\n\n"
        f"📦 Тариф: {plan['label']}\n\n"
        f"🔑 *Ваш WireGuard конфиг:*\n"
        f"```\n{vpn_config}\n```\n\n"
        f"📱 Скачайте WireGuard и вставьте конфиг.\n"
        f"Нужна помощь? @starlink\\_support",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Starlink VPN*\n\n"
        "/start — главное меню\n"
        "/buy — купить подписку\n"
        "/help — помощь\n\n"
        "Поддержка: @starlink_support",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))
    print("Бот запущен...")
    app.run_polling()
