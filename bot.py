import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.executor import start_polling
import os
import json

# ========== КОНФИГ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = [8493522297, 5449297683]  # ВАШИ ID
YUMONEY_LINK = "https://yoomoney.ru/to/4100119525707659"

# ========== БАЗА ДАННЫХ ==========
DATA_FILE = "shop_data.json"
KEYS_FILE = "keys_data.json"
USED_KEYS_FILE = "used_keys.json"
USERS_FILE = "users.json"
PENDING_FILE = "pending_payments.json"

os.makedirs("data", exist_ok=True)

def load_data():
    if not os.path.exists(DATA_FILE):
        default = {
            "prices": {
                "1day": 270,
                "7day": 1350,
                "14day": 2550,
                "forever": "на заказ"
            }
        }
        save_data(default)
        return default
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_keys():
    if not os.path.exists(KEYS_FILE):
        default = {
            "1day": ["DEMO_KEY_001", "DEMO_KEY_002"],
            "7day": ["DEMO_KEY_7DAY_001"],
            "14day": [],
            "forever": []
        }
        save_keys(default)
        return default
    with open(KEYS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_keys(keys):
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=4, ensure_ascii=False)

def load_users():
    if not os.path.exists(USERS_FILE):
        save_users([])
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def load_pending():
    if not os.path.exists(PENDING_FILE):
        save_pending([])
        return []
    with open(PENDING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_pending(pending):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(pending, f, indent=4, ensure_ascii=False)

def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)
        # Отправляем уведомление админам о новом пользователе
        for admin in ADMINS:
            try:
                bot.send_message(admin, f"🆕 Новый пользователь: [{user_id}](tg://user?id={user_id})", parse_mode="Markdown")
            except:
                pass

def get_and_remove_key(tarif):
    keys = load_keys()
    if not keys.get(tarif) or len(keys[tarif]) == 0:
        return None
    key = keys[tarif].pop(0)
    save_keys(keys)
    return key

def add_key(tarif, key):
    keys = load_keys()
    if tarif not in keys:
        keys[tarif] = []
    keys[tarif].append(key)
    save_keys(keys)

def get_keys_count():
    keys = load_keys()
    return {
        "1day": len(keys.get("1day", [])),
        "7day": len(keys.get("7day", [])),
        "14day": len(keys.get("14day", [])),
        "forever": len(keys.get("forever", []))
    }

# ========== КНОПКИ ==========
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🛒 МАГАЗИН", callback_data="shop"),
        InlineKeyboardButton("📞 ПОДДЕРЖКА", callback_data="support")
    )
    return kb

def shop_buttons():
    keys_count = get_keys_count()
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(f"💎 1 день — 270₽ [{keys_count['1day']}]", callback_data="buy_1day"),
        InlineKeyboardButton(f"🔥 7 дней — 1350₽ [{keys_count['7day']}]", callback_data="buy_7day"),
        InlineKeyboardButton(f"⚡ 14 дней — 2550₽ [{keys_count['14day']}]", callback_data="buy_14day"),
        InlineKeyboardButton(f"👑 Навсегда — на заказ", callback_data="buy_forever"),
        InlineKeyboardButton("◀️ ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu")
    )
    return kb

def admin_panel():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💰 ИЗМЕНИТЬ ЦЕНЫ", callback_data="admin_prices"),
        InlineKeyboardButton("🔑 ДОБАВИТЬ КЛЮЧИ", callback_data="admin_add_keys"),
        InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="admin_stats"),
        InlineKeyboardButton("📢 РАССЫЛКА", callback_data="admin_mailing"),
        InlineKeyboardButton("⏳ ОЖИДАЮТ ОПЛАТЫ", callback_data="admin_pending"),
        InlineKeyboardButton("◀️ ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu")
    )
    return kb

# ========== БОТ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

temp_states = {}

# ========== ДИАГНОСТИКА ==========
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    add_user(user_id)
    
    # Отправляем приветствие
    text = (
        "🌟 *ДОБРО ПОЖАЛОВАТЬ В МАГАЗИН ЧИТОВ* 🌟\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎮 Лучшие читы для твоей игры\n"
        "⚡ Анти-бан гарантия\n"
        "💬 Круглосуточная поддержка\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 *Выберите действие ниже* 👇"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu())
    
    # Отправляем тестовое сообщение админам
    for admin in ADMINS:
        try:
            await bot.send_message(
                admin,
                f"✅ *БОТ ЗАПУЩЕН* ✅\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Новый пользователь: [{user_id}](tg://user?id={user_id})\n"
                f"📛 Имя: {message.from_user.first_name}\n"
                f"🔗 Username: @{message.from_user.username}",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Ошибка отправки админу {admin}: {e}")

# ========== АДМИН КОМАНДА ==========
@dp.message_handler(commands=["admin"])
async def admin_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ADMINS:
        await message.answer(
            "🔧 *ПАНЕЛЬ АДМИНИСТРАТОРА* 🔧\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ Вы авторизованы как администратор\n\n"
            "Выберите действие:",
            parse_mode="Markdown",
            reply_markup=admin_panel()
        )
    else:
        await message.answer(
            "❌ *ДОСТУП ЗАПРЕЩЁН* ❌\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "У вас нет прав администратора.",
            parse_mode="Markdown"
        )

# ========== ГЛАВНОЕ МЕНЮ ==========
@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    text = (
        "🌟 *ГЛАВНОЕ МЕНЮ* 🌟\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Выберите действие:"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu())
    await callback.answer()

# ========== МАГАЗИН ==========
@dp.callback_query_handler(lambda c: c.data == "shop")
async def show_shop(callback: types.CallbackQuery):
    prices = load_data()["prices"]
    keys_count = get_keys_count()
    text = (
        "🛒 *АКТУАЛЬНЫЕ ЦЕНЫ* 🛒\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 *1 день* — {prices['1day']}₽  |  в наличии: {keys_count['1day']} шт.\n"
        f"🔥 *7 дней* — {prices['7day']}₽  |  в наличии: {keys_count['7day']} шт.\n"
        f"⚡ *14 дней* — {prices['14day']}₽  |  в наличии: {keys_count['14day']} шт.\n"
        f"👑 *Навсегда* — {prices['forever']}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ Нажмите на тариф для покупки"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=shop_buttons())
    await callback.answer()

# ========== ПОКУПКА ==========
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def buy_tariff(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    tarif = callback.data.split("_")[1]
    
    prices = load_data()["prices"]
    
    if tarif == "forever":
        text = (
            "👑 *ТАРИФ НАВСЕГДА* 👑\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Свяжитесь с администратором для обсуждения цены:\n"
            f"[💬 Написать админу](tg://user?id={ADMINS[0]})\n\n"
            "Обычно цена от 5000₽ и выше."
        )
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=shop_buttons())
        await callback.answer()
        return
    
    price = prices.get(tarif)
    if not price:
        await callback.answer("❌ Тариф временно недоступен")
        return
    
    keys_count = get_keys_count()
    if keys_count[tarif] == 0:
        await callback.message.answer(
            "❌ *КЛЮЧИ ЗАКОНЧИЛИСЬ* ❌\n"
            "Напишите в поддержку, администратор пополнит запасы.\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"[📞 Написать в поддержку](tg://user?id={ADMINS[0]})",
            parse_mode="Markdown",
            reply_markup=shop_buttons()
        )
        await callback.answer()
        return
    
    pending = load_pending()
    pending.append({
        "user_id": user_id,
        "tarif": tarif,
        "price": price,
        "status": "waiting"
    })
    save_pending(pending)
    
    text = (
        "💸 *ОПЛАТА* 💸\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Сумма: *{price}₽*\n"
        f"🎫 Тариф: *{tarif}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 [👉 НАЖМИТЕ ДЛЯ ОПЛАТЫ 👈]({YUMONEY_LINK})\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *ИНСТРУКЦИЯ:*\n"
        "1️⃣ Переведите *ровно указанную сумму* на кошелек\n"
        "2️⃣ Скопируйте **номер операции**\n"
        "3️⃣ Отправьте его сюда одним сообщением\n\n"
        "📝 Пример: `1234567-890123456`"
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

# ========== ПРИЁМ НОМЕРА ОПЕРАЦИИ ==========
@dp.message_handler()
async def handle_transaction(message: types.Message):
    user_id = message.from_user.id
    
    pending = load_pending()
    user_pending = [p for p in pending if p["user_id"] == user_id and p["status"] == "waiting"]
    
    if not user_pending:
        return
    
    transaction = message.text.strip()
    pending_item = user_pending[0]
    
    # Отправляем админам
    for admin in ADMINS:
        try:
            text = (
                "💰 *НОВАЯ ОПЛАТА* 💰\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Пользователь: [{user_id}](tg://user?id={user_id})\n"
                f"📛 Имя: {message.from_user.first_name}\n"
                f"🎫 Тариф: {pending_item['tarif']}\n"
                f"💵 Сумма: {pending_item['price']}₽\n"
                f"📝 Номер операции: `{transaction}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *Чтобы выдать ключ* — ответьте на это сообщение\n"
                "❌ *Чтобы отклонить* — ответьте: `отказ`"
            )
            await bot.send_message(admin, text, parse_mode="Markdown")
        except Exception as e:
            print(f"Ошибка отправки админу {admin}: {e}")
    
    for p in pending:
        if p["user_id"] == user_id and p["status"] == "waiting":
            p["status"] = "sent"
            p["transaction"] = transaction
            break
    save_pending(pending)
    
    await message.answer(
        "✅ *НОМЕР ОПЕРАЦИИ ПОЛУЧЕН* ✅\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Администратор проверит платёж и выдаст ключ.\n"
        "Обычно это занимает 5-15 минут.\n\n"
        "Спасибо за ожидание! 🙏"
    )

# ========== АДМИН: ВЫДАТЬ КЛЮЧ ==========
@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and msg.reply_to_message)
async def admin_reply(message: types.Message):
    reply_text = message.reply_to_message.text or ""
    
    match = re.search(r"Пользователь: \[(\d+)\]", reply_text)
    if not match:
        await message.answer("❌ Ответьте на сообщение с оплатой")
        return
    
    user_id = int(match.group(1))
    
    tarif_match = re.search(r"Тариф: (\w+)", reply_text)
    if not tarif_match:
        await message.answer("❌ Не найден тариф")
        return
    tarif = tarif_match.group(1)
    
    if message.text.lower().strip() == "отказ":
        await bot.send_message(
            user_id,
            "❌ *ПЛАТЁЖ НЕ ПОДТВЕРЖДЁН* ❌\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Проверьте сумму или обратитесь в поддержку.",
            parse_mode="Markdown"
        )
        await message.answer(f"❌ Платёж пользователя {user_id} отклонён")
        pending = load_pending()
        pending = [p for p in pending if p["user_id"] != user_id]
        save_pending(pending)
        return
    
    key = get_and_remove_key(tarif)
    if key:
        await bot.send_message(
            user_id,
            f"✅ *КЛЮЧ ПОЛУЧЕН* ✅\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎮 Ваш ключ: `{key}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Спасибо за покупку! Приятной игры! 🎉",
            parse_mode="Markdown"
        )
        await message.answer(f"✅ Ключ выдан пользователю {user_id}")
        pending = load_pending()
        pending = [p for p in pending if p["user_id"] != user_id]
        save_pending(pending)
    else:
        await message.answer("❌ Ключи закончились! Добавьте через админ-панель.")

# ========== АДМИН: ОСТАЛЬНЫЕ ФУНКЦИИ ==========
@dp.callback_query_handler(lambda c: c.data == "admin_pending")
async def show_pending(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Доступ запрещён")
        return
    pending = load_pending()
    waiting = [p for p in pending if p["status"] == "waiting"]
    sent = [p for p in pending if p["status"] == "sent"]
    
    text = "⏳ *ОЖИДАЮТ ОПЛАТЫ:*\n"
    if waiting:
        for p in waiting:
            text += f"└ 👤 {p['user_id']} — {p['tarif']} — {p['price']}₽\n"
    else:
        text += "└ Нет\n"
    
    text += "\n📤 *ОТПРАВИЛИ НОМЕР (ждут ключ):*\n"
    if sent:
        for p in sent:
            text += f"└ 👤 {p['user_id']} — {p['tarif']} — {p['price']}₽\n"
    else:
        text += "└ Нет"
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_panel())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_prices")
async def admin_prices(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Доступ запрещён")
        return
    await callback.message.answer(
        "💰 *ИЗМЕНЕНИЕ ЦЕН* 💰\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Введите 4 значения через пробел:\n"
        "`1день 7дней 14дней навсегда`\n\n"
        "Пример: `270 1350 2550 на_заказ`",
        parse_mode="Markdown"
    )
    temp_states[callback.from_user.id] = "waiting_prices"
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_add_keys")
async def admin_keys(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Доступ запрещён")
        return
    await callback.message.answer(
        "🔑 *ДОБАВЛЕНИЕ КЛЮЧЕЙ* 🔑\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Введите: `тариф ключ`\n"
        "Тарифы: `1day`, `7day`, `14day`, `forever`\n\n"
        "Пример: `1day ABC123-xyz`\n"
        "Для завершения введите `готово`",
        parse_mode="Markdown"
    )
    temp_states[callback.from_user.id] = "waiting_keys"
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Доступ запрещён")
        return
    keys_count = get_keys_count()
    users = len(load_users())
    pending = len([p for p in load_pending() if p["status"] == "waiting"])
    
    text = (
        "📊 *СТАТИСТИКА* 📊\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Пользователей: *{users}*\n"
        f"⏳ Ожидают оплаты: *{pending}*\n\n"
        "🔑 *Ключи в наличии:*\n"
        f"└ 💎 1 день: *{keys_count['1day']}* шт.\n"
        f"└ 🔥 7 дней: *{keys_count['7day']}* шт.\n"
        f"└ ⚡ 14 дней: *{keys_count['14day']}* шт.\n"
        f"└ 👑 Навсегда: *{keys_count['forever']}* шт."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_panel())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_mailing")
async def admin_mailing(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Доступ запрещён")
        return
    await callback.message.answer("📢 Введите текст для рассылки (поддерживается Markdown):")
    temp_states[callback.from_user.id] = "waiting_mailing"
    await callback.answer()

# ========== ОБРАБОТКА ВВОДА АДМИНОВ ==========
@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and temp_states.get(msg.from_user.id) == "waiting_prices")
async def save_prices(message: types.Message):
    parts = message.text.split(maxsplit=3)
    if len(parts) == 4 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
        data = load_data()
        data["prices"] = {
            "1day": int(parts[0]),
            "7day": int(parts[1]),
            "14day": int(parts[2]),
            "forever": parts[3]
        }
        save_data(data)
        await message.answer("✅ Цены сохранены!", reply_markup=admin_panel())
        del temp_states[message.from_user.id]
    else:
        await message.answer("❌ Ошибка! Введите 4 значения через пробел (первые 3 — цифры)")

@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and temp_states.get(msg.from_user.id) == "waiting_keys")
async def save_keys(message: types.Message):
    if message.text.lower() == "готово":
        await message.answer("✅ Ключи сохранены!", reply_markup=admin_panel())
        del temp_states[message.from_user.id]
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) == 2 and parts[0] in ["1day", "7day", "14day", "forever"]:
        add_key(parts[0], parts[1])
        keys_count = get_keys_count()
        await message.answer(f"✅ Ключ добавлен для *{parts[0]}*. Теперь: {keys_count[parts[0]]} шт.\n\nВведите следующий или `готово`", parse_mode="Markdown")
    else:
        await message.answer("❌ Формат: `1day ABC123`")

@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and temp_states.get(msg.from_user.id) == "waiting_mailing")
async def send_mailing(message: types.Message):
    users = load_users()
    ok = 0
    fail = 0
    await message.answer(f"⏳ Начинаю рассылку для {len(users)} пользователей...")
    for uid in users:
        try:
            await bot.send_message(uid, message.text, parse_mode="Markdown")
            ok += 1
            await asyncio.sleep(0.05)
        except:
            fail += 1
    await message.answer(f"✅ Рассылка завершена!\n✅ Успешно: {ok}\n❌ Ошибок: {fail}", reply_markup=admin_panel())
    del temp_states[message.from_user.id]

# ========== ПОДДЕРЖКА ==========
@dp.callback_query_handler(lambda c: c.data == "support")
async def support(callback: types.CallbackQuery):
    text = (
        "📞 *ПОДДЕРЖКА* 📞\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Напишите ваше сообщение ниже.\n"
        "Администраторы ответят вам как можно скорее!\n\n"
        "💬 *Просто отправьте текст или файл*"
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    temp_states[callback.from_user.id] = "support_wait"
    await callback.answer()

@dp.message_handler(lambda msg: temp_states.get(msg.from_user.id) == "support_wait")
async def forward_support(message: types.Message):
    user = message.from_user
    text = (
        "📞 *НОВОЕ ОБРАЩЕНИЕ* 📞\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 ID: `{user.id}`\n"
        f"📛 Имя: {user.first_name}\n"
        f"🔗 Username: @{user.username}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 *Сообщение:*\n{message.text}"
    )
    for admin in ADMINS:
        try:
            await bot.send_message(admin, text, parse_mode="Markdown")
        except Exception as e:
            print(f"Ошибка отправки админу {admin}: {e}")
    await message.answer(
        "✅ *СООБЩЕНИЕ ОТПРАВЛЕНО* ✅\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Администраторы скоро ответят вам!",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    del temp_states[message.from_user.id]

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🚀 Бот запускается...")
    print(f"👥 Админы: {ADMINS}")
    start_polling(dp, skip_updates=True)
