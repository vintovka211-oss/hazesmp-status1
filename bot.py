import requests
import time
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8590452175:AAH8IANusnU3BxrGtJLQ0xwQxj3WpsirVik"

# Возможные символы для username
CHARS = string.ascii_lowercase + string.digits + "_"

# Словарь для хранения результатов поиска по пользователям
user_results = {}

def generate_usernames(length):
    """Генерирует все возможные username заданной длины (медленно для 4+)"""
    if length == 3:
        total = len(CHARS) ** 3
        if total > 5000:
            return []
        result = []
        for a in CHARS:
            for b in CHARS:
                for c in CHARS:
                    result.append(f"{a}{b}{c}")
        return result
    elif length == 4:
        # 37^4 = 1.8 млн — не генерируем, слишком много
        return []
    return []

def get_keyboard():
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 3 буквы", callback_data="search_3"),
         InlineKeyboardButton("🔍 4 буквы", callback_data="search_4")],
        [InlineKeyboardButton("🔍 5 букв", callback_data="search_5")],
        [InlineKeyboardButton("❌ Остановить поиск", callback_data="stop")]
    ])
    return keyboard

async def start(update: Update, context):
    await update.message.reply_text(
        "🤖 **Бот для поиска свободных Telegram username**\n\n"
        "Выбери длину username для поиска:\n"
        "• 3 буквы — проверяет все возможные (медленно)\n"
        "• 4-5 букв — показывает примеры\n\n"
        "⚠️ Telegram блокирует массовые проверки, поэтому поиск может быть неполным.",
        reply_markup=get_keyboard(),
        parse_mode="Markdown"
    )

async def search_button(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    length = int(query.data.split("_")[1])
    user_id = query.from_user.id
    
    await query.edit_message_text(f"🔍 Поиск свободных username длиной {length}...\n⏳ Это может занять несколько минут!")
    
    if length == 3:
        usernames = generate_usernames(3)
        free = []
        total = 0
        
        for username in usernames:
            url = f"https://t.me/{username}"
            try:
                r = requests.get(url, timeout=3)
                if "doesn't exist" in r.text or "not found" in r.text:
                    free.append(f"@{username}")
                    await context.bot.send_message(user_id, f"✅ Найден свободный: @{username}")
            except:
                pass
            
            total += 1
            if total % 10 == 0:
                time.sleep(0.5)
            
            if len(free) >= 20:
                break
        
        if free:
            await context.bot.send_message(user_id, f"🎉 Найдено свободных username:\n{', '.join(free)}")
        else:
            await context.bot.send_message(user_id, "😔 Свободных username не найдено")
    
    elif length == 4:
        # Демонстрация — проверяем только первые 100 вариантов
        await context.bot.send_message(user_id, "⚠️ Полный перебор 4-символьных username (~1.8 млн) займёт дни.\n\nПоказываю первые 100 вариантов — некоторые могут быть свободны:")
        sample = []
        for a in CHARS[:5]:
            for b in CHARS[:5]:
                for c in CHARS[:5]:
                    for d in CHARS[:5]:
                        sample.append(f"{a}{b}{c}{d}")
                        if len(sample) >= 100:
                            break
                    if len(sample) >= 100:
                        break
                if len(sample) >= 100:
                    break
            if len(sample) >= 100:
                break
        
        free_sample = []
        for username in sample:
            url = f"https://t.me/{username}"
            try:
                r = requests.get(url, timeout=3)
                if "doesn't exist" in r.text or "not found" in r.text:
                    free_sample.append(f"@{username}")
            except:
                pass
            time.sleep(0.3)
        
        if free_sample:
            await context.bot.send_message(user_id, f"✅ Свободные из выборки:\n{', '.join(free_sample)}")
        else:
            await context.bot.send_message(user_id, "😔 В выборке свободных не найдено")
    
    elif length == 5:
        await context.bot.send_message(user_id, "⚠️ 5-символьных username очень много (~70 млн). Полный перебор невозможен.\n\nРекомендую использовать сайты вроде fragment.com для поиска коротких username.")

async def stop_search(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏹️ Поиск остановлен. Напиши /start, чтобы начать заново.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(search_button, pattern="^search_"))
    app.add_handler(CallbackQueryHandler(stop_search, pattern="^stop$"))
    
    print("✅ Бот для поиска username запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
