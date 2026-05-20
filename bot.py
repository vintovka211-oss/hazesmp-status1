import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.executor import start_polling
import os
import json

# === КОНФИГ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = [8493522297, 5449297683]
YUMONEY_LINK = "https://yoomoney.ru/to/4100119525707659"

# === БАЗА ДАННЫХ ===
DATA_FILE = "shop_data.json"
KEYS_FILE = "keys_data.json"
USED_KEYS_FILE = "used_keys.json"
USERS_FILE = "users.json"
PENDING_FILE = "pending_payments.json"

os.makedirs("data", exist_ok=True)

def load_data():
    if not os.path.exists(DATA_FILE):
        default = {"prices": {"1day": 100, "7day": 500, "30day": 1500, "forever": 5000}}
        save_data(default)
        return default
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_keys():
    if not os.path.exists(KEYS_FILE):
        default = {"1day": ["DEMO_KEY_001"], "7day": [], "30day": [], "forever": []}
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

# === КНОПКИ ===
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
        InlineKeyboardButton("📞 Поддержка", callback_data="support")
    )
    return kb

def shop_buttons():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💎 1 день", callback_data="buy_1day"),
        InlineKeyboardButton("🔥 7 дней", callback_data="buy_7day"),
        InlineKeyboardButton("⚡ 30 дней", callback_data="buy_30day"),
        InlineKeyboardButton("👑 Навсегда", callback_data="buy_forever"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
    )
    return kb

def admin_panel():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💰 Изменить цены", callback_data="admin_prices"),
        InlineKeyboardButton("🔑 Добавить ключи", callback_data="admin_add_keys"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("📢 Рассылка", callback_data="admin_mailing"),
        InlineKeyboardButton("⏳ Ожидают оплаты", callback_data="admin_pending"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
    )
    return kb

# === БОТ ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

temp_states = {}

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    await message.answer(
        "🎮 *Добро пожаловать в магазин!*\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎮 *Главное меню*",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "shop")
async def show_shop(callback: types.CallbackQuery):
    prices = load_data()["prices"]
    text = (f"🛒 *Цены:*\n\n"
            f"💎 1 день — {prices['1day']}₽\n"
            f"🔥 7 дней — {prices['7day']}₽\n"
            f"⚡ 30 дней — {prices['30day']}₽\n"
            f"👑 Навсегда — {prices['forever']}₽\n\n"
            f"Нажмите на тариф")
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=shop_buttons())
    await callback.answer()

# --- ПОКУПКА ---
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def buy_tariff(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    tarif = callback.data.split("_")[1]
    price = load_data()["prices"][tarif]
    
    keys = load_keys()
    if not keys.get(tarif) or len(keys[tarif]) == 0:
        await callback.message.answer("❌ Ключи закончились. Напишите в поддержку!", reply_markup=main_menu())
        return
    
    # Сохраняем заказ
    pending = load_pending()
    pending.append({
        "user_id": user_id,
        "tarif": tarif,
        "price": price,
        "status": "waiting"
    })
    save_pending(pending)
    
    text = (f"💸 *Оплата: {price}₽*\n\n"
            f"🔗 [Нажмите для оплаты]({YUMONEY_LINK})\n\n"
            f"📌 *Инструкция:*\n"
            f"1. Переведите *{price}₽* на кошелек\n"
            f"2. Скопируйте **номер операции** (придет в смс/в истории)\n"
            f"3. Отправьте его сюда одним сообщением\n\n"
            f"Пример: `1234567-890123456`")
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

# --- ПРИЁМ НОМЕРА ОПЕРАЦИИ ---
@dp.message_handler()
async def handle_transaction(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, есть ли ожидающий платёж у пользователя
    pending = load_pending()
    user_pending = [p for p in pending if p["user_id"] == user_id and p["status"] == "waiting"]
    
    if not user_pending:
        return
    
    transaction = message.text.strip()
    pending_item = user_pending[0]
    
    # Отправляем админам
    for admin in ADMINS:
        text = (f"💰 *НОВАЯ ОПЛАТА*\n\n"
                f"👤 Пользователь: [{user_id}](tg://user?id={user_id})\n"
                f"📛 Имя: {message.from_user.first_name}\n"
                f"🎫 Тариф: {pending_item['tarif']}\n"
                f"💵 Сумма: {pending_item['price']}₽\n"
                f"📝 Номер операции: `{transaction}`\n\n"
                f"✅ Чтобы выдать ключ — **ответьте на это сообщение**\n"
                f"❌ Чтобы отклонить — ответьте: `отказ`")
        await bot.send_message(admin, text, parse_mode="Markdown")
    
    # Обновляем статус
    for p in pending:
        if p["user_id"] == user_id and p["status"] == "waiting":
            p["status"] = "sent"
            p["transaction"] = transaction
            break
    save_pending(pending)
    
    await message.answer("✅ Номер операции отправлен администраторам. Ключ придет в течение 5-15 минут.")

# --- АДМИН: ВЫДАТЬ КЛЮЧ (ответом на сообщение) ---
@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and msg.reply_to_message)
async def admin_reply(message: types.Message):
    reply_text = message.reply_to_message.text or ""
    
    # Ищем ID пользователя
    match = re.search(r"Пользователь: \[(\d+)\]", reply_text)
    if not match:
        await message.answer("❌ Ответьте на сообщение с оплатой")
        return
    
    user_id = int(match.group(1))
    
    # Ищем тариф
    tarif_match = re.search(r"Тариф: (\w+)", reply_text)
    if not tarif_match:
        await message.answer("❌ Не найден тариф")
        return
    tarif = tarif_match.group(1)
    
    # Если админ написал "отказ"
    if message.text.lower().strip() == "отказ":
        await bot.send_message(user_id, "❌ Ваш платёж не подтверждён. Проверьте сумму или обратитесь в поддержку.")
        await message.answer(f"❌ Платёж пользователя {user_id} отклонён")
        
        # Удаляем из ожидающих
        pending = load_pending()
        pending = [p for p in pending if p["user_id"] != user_id]
        save_pending(pending)
        return
    
    # Выдаём ключ
    key = get_and_remove_key(tarif)
    if key:
        await bot.send_message(user_id, f"✅ *Ваш ключ:*\n`{key}`\n\nСпасибо за покупку!", parse_mode="Markdown")
        await message.answer(f"✅ Ключ выдан пользователю {user_id}")
        
        # Удаляем из ожидающих
        pending = load_pending()
        pending = [p for p in pending if p["user_id"] != user_id]
        save_pending(pending)
    else:
        await message.answer("❌ Ключи закончились! Добавьте через админ-панель.")

# --- АДМИН: ОЖИДАЮТ ОПЛАТЫ ---
@dp.callback_query_handler(lambda c: c.data == "admin_pending")
async def show_pending(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return
    pending = load_pending()
    waiting = [p for p in pending if p["status"] == "waiting"]
    sent = [p for p in pending if p["status"] == "sent"]
    
    text = "⏳ *Ожидают оплаты:*\n"
    if waiting:
        for p in waiting:
            text += f"👤 {p['user_id']} — {p['tarif']} — {p['price']}₽\n"
    else:
        text += "Нет\n"
    
    text += "\n📤 *Отправили номер (ждут ключ):*\n"
    if sent:
        for p in sent:
            text += f"👤 {p['user_id']} — {p['tarif']} — {p['price']}₽\n"
    else:
        text += "Нет"
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_panel())
    await callback.answer()

# --- АДМИН-ПАНЕЛЬ (остальное) ---
@dp.message_handler(commands=["admin"])
async def admin_cmd(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("🔧 *Панель администратора*", parse_mode="Markdown", reply_markup=admin_panel())

@dp.callback_query_handler(lambda c: c.data == "admin_prices")
async def admin_prices(callback: types.CallbackQuery):
    if callback.from_user.id in ADMINS:
        await callback.message.answer("Введите 4 числа: `100 500 1500 5000`", parse_mode="Markdown")
        temp_states[callback.from_user.id] = "waiting_prices"
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_add_keys")
async def admin_keys(callback: types.CallbackQuery):
    if callback.from_user.id in ADMINS:
        await callback.message.answer("Введите: `тариф ключ`\nТарифы: 1day, 7day, 30day, forever\nДля завершения `готово`", parse_mode="Markdown")
        temp_states[callback.from_user.id] = "waiting_keys"
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id in ADMINS:
        keys = load_keys()
        users = len(load_users())
        text = f"📊 *Статистика*\n👥 Пользователей: {users}\n"
        for t, k in keys.items():
            text += f"{t}: {len(k)} ключей\n"
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_panel())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_mailing")
async def admin_mailing(callback: types.CallbackQuery):
    if callback.from_user.id in ADMINS:
        await callback.message.answer("Введите текст рассылки:")
        temp_states[callback.from_user.id] = "waiting_mailing"
    await callback.answer()

@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and temp_states.get(msg.from_user.id) == "waiting_prices")
async def save_prices(message: types.Message):
    parts = message.text.split()
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        data = load_data()
        data["prices"] = {"1day": int(parts[0]), "7day": int(parts[1]), "30day": int(parts[2]), "forever": int(parts[3])}
        save_data(data)
        await message.answer("✅ Цены сохранены", reply_markup=admin_panel())
        del temp_states[message.from_user.id]
    else:
        await message.answer("❌ Ошибка. Введите 4 числа")

@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and temp_states.get(msg.from_user.id) == "waiting_keys")
async def save_keys(message: types.Message):
    if message.text.lower() == "готово":
        await message.answer("✅ Готово", reply_markup=admin_panel())
        del temp_states[message.from_user.id]
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) == 2 and parts[0] in ["1day", "7day", "30day", "forever"]:
        add_key(parts[0], parts[1])
        await message.answer(f"✅ Добавлен. Осталось: {len(load_keys()[parts[0]])}")
    else:
        await message.answer("❌ Формат: `1day ABC123`")

@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and temp_states.get(msg.from_user.id) == "waiting_mailing")
async def send_mailing(message: types.Message):
    users = load_users()
    ok = 0
    for uid in users:
        try:
            await bot.send_message(uid, message.text, parse_mode="Markdown")
            ok += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.answer(f"✅ Рассылка: {ok}/{len(users)}", reply_markup=admin_panel())
    del temp_states[message.from_user.id]

# --- ПОДДЕРЖКА ---
@dp.callback_query_handler(lambda c: c.data == "support")
async def support(callback: types.CallbackQuery):
    await callback.message.edit_text("📞 *Напишите ваше сообщение:*", parse_mode="Markdown")
    temp_states[callback.from_user.id] = "support_wait"
    await callback.answer()

@dp.message_handler(lambda msg: temp_states.get(msg.from_user.id) == "support_wait")
async def forward_support(message: types.Message):
    user = message.from_user
    text = f"📞 *Обращение от* {user.id}\n📛 {user.first_name}\n💬 {message.text}"
    for admin in ADMINS:
        await bot.send_message(admin, text, parse_mode="Markdown")
    await message.answer("✅ Отправлено")
    del temp_states[message.from_user.id]

# --- ЗАПУСК ---
if __name__ == "__main__":
    start_polling(dp, skip_updates=True)
