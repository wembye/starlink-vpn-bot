import os
import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, LabeledPrice
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = "8716311827:AAHemWBB9X8srTr8pqmaHz4Zhj1F_T7exVA"
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://project-nv8gi.vercel.app/")
ADMIN_ID = 5396498498

PLANS = {
    "trial":   {"stars": 1,    "label": "Пробный период (8 часов)", "days": 0},
    "month":   {"stars": 200,  "label": "1 месяц",                  "days": 30},
    "quarter": {"stars": 500,  "label": "3 месяца",                 "days": 90},
    "year":    {"stars": 1600, "label": "1 год",                    "days": 365},
}

# Simple in-memory stats (resets on restart)
# For persistent stats, use a database
stats = {
    "users": {},       # user_id -> {name, username, first_seen, last_seen, payments}
    "total_payments": 0,
    "revenue_stars": 0,
    "starts": 0,
}

def save_user(user):
    uid = str(user.id)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    if uid not in stats["users"]:
        stats["users"][uid] = {
            "name": user.first_name or "",
            "username": f"@{user.username}" if user.username else "—",
            "first_seen": now,
            "last_seen": now,
            "payments": 0,
            "stars_spent": 0,
        }
    else:
        stats["users"][uid]["last_seen"] = now

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    stats["starts"] += 1

    first_name = user.first_name or ""
    username = f"@{user.username}" if user.username else first_name
    import urllib.parse
    user_data = f"id={user.id}&name={urllib.parse.quote(username)}&first={urllib.parse.quote(first_name)}"
    webapp_url = f"{WEB_APP_URL}?user={urllib.parse.quote(user_data)}"

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
        f"🌐 Безлимит устройств · Без логов\n\n"
        f"Нажми кнопку чтобы выбрать тариф:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет доступа.")
        return

    total_users = len(stats["users"])
    total_starts = stats["starts"]
    total_payments = stats["total_payments"]
    total_stars = stats["revenue_stars"]

    # Recent users (last 5)
    recent = list(stats["users"].values())[-5:]
    recent_text = ""
    for u in reversed(recent):
        recent_text += f"\n• {u['name']} {u['username']} — {u['last_seen']}"

    text = (
        f"📊 *Статистика Starlink VPN*\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"👥 *Пользователей:* {total_users}\n"
        f"🚀 *Запусков бота:* {total_starts}\n"
        f"💳 *Оплат:* {total_payments}\n"
        f"⭐ *Заработано Stars:* {total_stars}\n\n"
        f"🕐 *Последние пользователи:*{recent_text if recent_text else ' —'}\n\n"
        f"⏰ Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

    keyboard = [[
        InlineKeyboardButton("📋 Все пользователи", callback_data="admin_users"),
        InlineKeyboardButton("💰 Платежи", callback_data="admin_payments"),
    ], [
        InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
    ]]

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "admin_users":
        if query.from_user.id != ADMIN_ID:
            return
        users = stats["users"]
        if not users:
            await query.message.reply_text("Пользователей пока нет.")
            return
        text = f"👥 *Все пользователи ({len(users)}):*\n\n"
        for uid, u in list(users.items())[-20:]:
            text += f"• {u['name']} {u['username']}\n  ID: {uid} · с {u['first_seen']}\n  Платежей: {u['payments']} · Stars: {u['stars_spent']}\n\n"
        await query.message.reply_text(text[:4000], parse_mode="Markdown")

    elif query.data == "admin_payments":
        if query.from_user.id != ADMIN_ID:
            return
        text = (
            f"💰 *Финансы*\n\n"
            f"Всего платежей: {stats['total_payments']}\n"
            f"Всего Stars: {stats['revenue_stars']} ⭐\n"
            f"≈ USD: ${stats['revenue_stars'] * 0.013:.2f}"
        )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif query.data == "admin_broadcast":
        if query.from_user.id != ADMIN_ID:
            return
        await query.message.reply_text(
            "📢 Для рассылки отправь:\n`/broadcast Текст сообщения`",
            parse_mode="Markdown"
        )

    elif query.data.startswith("buy_"):
        plan_id = query.data.replace("buy_", "")
        plan = PLANS.get(plan_id)
        if not plan:
            return
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=f"Starlink VPN — {plan['label']}",
            description=f"VPN подписка: {plan['label']}. WireGuard, безлимит устройств, без логов.",
            payload=f"vpn_{plan_id}_{query.from_user.id}",
            currency="XTR",
            prices=[LabeledPrice(label=plan['label'], amount=plan['stars'])],
            provider_token="",
        )

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Использование: /broadcast Текст")
        return
    text = " ".join(context.args)
    sent = 0
    failed = 0
    for uid in stats["users"]:
        try:
            await context.bot.send_message(chat_id=int(uid), text=text)
            sent += 1
        except:
            failed += 1
    await update.message.reply_text(f"📢 Отправлено: {sent}\n❌ Ошибок: {failed}")

async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.effective_message.web_app_data.data
    user = update.effective_user
    save_user(user)
    try:
        payload = json.loads(data)
        plan_id = payload.get("plan")
        plan = PLANS.get(plan_id)
        if not plan:
            return
        keyboard = [[InlineKeyboardButton(
            text=f"⭐ Оплатить {plan['stars']} Stars",
            callback_data=f"buy_{plan_id}"
        )]]
        await update.message.reply_text(
            f"💳 *{plan['label']}* — {plan['stars']} ⭐\n\nНажми для оплаты через Telegram Stars:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"webapp_data error: {e}")

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    user = update.effective_user
    save_user(user)

    parts = payload.split("_")
    plan_id = parts[1] if len(parts) > 1 else "month"
    plan = PLANS.get(plan_id, PLANS["month"])

    # Update stats
    stats["total_payments"] += 1
    stats["revenue_stars"] += plan["stars"]
    uid = str(user.id)
    if uid in stats["users"]:
        stats["users"][uid]["payments"] += 1
        stats["users"][uid]["stars_spent"] += plan["stars"]

    vpn_config = (
        "[Interface]\n"
        "PrivateKey = wOEI9rqqbDwnN8/BdXXXXXXXXXX=\n"
        "Address = 10.66.66.2/32\n"
        "DNS = 1.1.1.1\n\n"
        "[Peer]\n"
        "PublicKey = JRI8Xc0zKP9kXk8qPXXXXXXXXXX=\n"
        "Endpoint = vpn.starlink.io:51820\n"
        "AllowedIPs = 0.0.0.0/0\n"
        "PersistentKeepalive = 25"
    )

    await update.message.reply_text(
        f"✅ *Оплата прошла! Спасибо!*\n\n"
        f"📦 Тариф: {plan['label']}\n\n"
        f"🔑 *Ваш WireGuard конфиг:*\n"
        f"```\n{vpn_config}\n```\n\n"
        f"📱 Скачайте WireGuard и вставьте конфиг.\n"
        f"Нужна помощь? @starlink\\_support",
        parse_mode="Markdown"
    )

    # Notify admin
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💰 Новая оплата!\n👤 {user.first_name} @{user.username or '—'}\n📦 {plan['label']}\n⭐ {plan['stars']} Stars"
        )
    except:
        pass

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Starlink VPN*\n\n"
        "/start — главное меню\n"
        "/help — помощь\n\n"
        "Поддержка: @starlink\\_support",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))
    print("Бот запущен...")
    app.run_polling()
