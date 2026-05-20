import asyncio
import uuid
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.executor import start_polling
from config import BOT_TOKEN, ADMINS, YKASSA_SHOP_ID, YKASSA_SECRET_KEY
from database import load_data, save_data, get_and_remove_key, add_key, load_keys, add_user, load_users

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Временные платежи
temp_payments = {}  # {user_id: {"tarif": "1day", "payment_id": "xxx"}}

# --- Создание платежа в ЮKassa ---
def create_payment(amount, description, user_id):
    """Создаёт платёж и возвращает ссылку на оплату"""
    idempotence_key = str(uuid.uuid4())
    
    auth = (YKASSA_SHOP_ID, YKASSA_SECRET_KEY)
    headers = {"Content-Type": "application/json"}
    
    data = {
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "payment_method_data": {
            "type": "bank_card"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/your_bot"  # Замените на ссылку на вашего бота
        },
        "description": f"Покупка чита | Пользователь {user_id}",
        "capture": True,
        "metadata": {
            "user_id": str(user_id),
            "tarif": description
        }
    }
    
    try:
        response = requests.post(
            "https://api.yookassa.ru/v3/payments",
            headers=headers,
            json=data,
            auth=auth
        )
        
        if response.status_code == 200 or response.status_code == 201:
            payment_data = response.json()
            return {
                "payment_id": payment_data["id"],
                "confirmation_url": payment_data["confirmation"]["confirmation_url"]
            }
        else:
            print(f"Ошибка ЮKassa: {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

# --- Проверка статуса платежа ---
def check_payment_status(payment_id):
    """Проверяет, оплачен ли платёж"""
    auth = (YKASSA_SHOP_ID, YKASSA_SECRET_KEY)
    
    try:
        response = requests.get(
            f"https://api.yookassa.ru/v3/payments/{payment_id}",
            auth=auth
        )
        
        if response.status_code == 200:
            payment_data = response.json()
            return payment_data.get("status") == "succeeded"
        return False
    except:
        return False

# --- Кнопки ---
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
        InlineKeyboardButton("📞 Поддержка", callback_data="support")
    )
    return keyboard

def shop_buttons():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💎 1 день", callback_data="buy_1day"),
        InlineKeyboardButton("🔥 7 дней", callback_data="buy_7day"),
        InlineKeyboardButton("⚡ 30 дней", callback_data="buy_30day"),
        InlineKeyboardButton("👑 Навсегда", callback_data="buy_forever"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
    )
    return keyboard

def admin_panel():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💰 Изменить цены", callback_data="admin_prices"),
        InlineKeyboardButton("🔑 Добавить ключи", callback_data="admin_add_keys"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("📢 Рассылка", callback_data="admin_mailing"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
    )
    return keyboard

# --- Старт ---
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    await message.answer(
        "🎮 *Добро пожаловать в магазин читов!*\n\n"
        "Выберите действие:",
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

# --- Магазин ---
@dp.callback_query_handler(lambda c: c.data == "shop")
async def show_shop(callback: types.CallbackQuery):
    data = load_data()
    prices = data["prices"]
    text = (f"🛒 *Актуальные цены:*\n\n"
            f"💎 1 день — {prices['1day']}₽\n"
            f"🔥 7 дней — {prices['7day']}₽\n"
            f"⚡ 30 дней — {prices['30day']}₽\n"
            f"👑 Навсегда — {prices['forever']}₽\n\n"
            f"Нажмите на тариф для покупки")
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=shop_buttons())
    await callback.answer()

# --- Покупка ---
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def buy_tariff(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    tarif = callback.data.split("_")[1]
    
    data = load_data()
    price = data["prices"][tarif]
    
    # Проверяем наличие ключей
    keys = load_keys()
    if not keys.get(tarif) or len(keys[tarif]) == 0:
        await callback.message.answer("❌ Ключи временно закончились. Напишите в поддержку!", reply_markup=main_menu())
        return
    
    # Создаём платёж в ЮKassa
    payment = create_payment(price, tarif, user_id)
    
    if not payment:
        await callback.message.answer("❌ Ошибка создания платежа. Попробуйте позже.")
        return
    
    # Сохраняем информацию о платеже
    temp_payments[user_id] = {
        "tarif": tarif,
        "payment_id": payment["payment_id"],
        "status": "waiting"
    }
    
    text = (f"💸 *Оплата: {price}₽*\n\n"
            f"🔗 *Ссылка для оплаты:*\n{payment['confirmation_url']}\n\n"
            f"После оплаты нажмите «Проверить оплату»")
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("✅ Проверить оплату", callback_data="check_payment"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_payment"),
        InlineKeyboardButton("◀️ Назад в магазин", callback_data="shop")
    )
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

# --- Проверка оплаты ---
@dp.callback_query_handler(lambda c: c.data == "check_payment")
async def check_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in temp_payments:
        await callback.answer("❌ Нет активного платежа", show_alert=True)
        return
    
    payment = temp_payments[user_id]
    
    await callback.message.answer("🔍 *Проверка платежа...*", parse_mode="Markdown")
    
    # Проверяем статус платежа
    if check_payment_status(payment["payment_id"]):
        # Платёж успешен, выдаём ключ
        key = get_and_remove_key(payment["tarif"])
        
        if key:
            await callback.message.answer(
                f"✅ *Оплата подтверждена!*\n\n"
                f"Ваш ключ:\n`{key}`\n\n"
                f"Спасибо за покупку!\n"
                f"Нажмите /start для нового заказа",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
            
            # Уведомляем админов
            for admin in ADMINS:
                await bot.send_message(admin, f"💰 Продажа! Пользователь {user_id} купил {payment['tarif']}")
        else:
            await callback.message.answer("❌ Ключи закончились. Напишите в поддержку!", reply_markup=main_menu())
        
        del temp_payments[user_id]
    else:
        await callback.message.answer(
            "⏳ *Платёж ещё не подтверждён*\n\n"
            "Перейдите по ссылке и оплатите.\n"
            "После оплаты нажмите «Проверить оплату» снова.\n\n"
            "Если вы уже оплатили — подождите 1-2 минуты.",
            parse_mode="Markdown"
        )

# --- Отмена платежа ---
@dp.callback_query_handler(lambda c: c.data == "cancel_payment")
async def cancel_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in temp_payments:
        del temp_payments[user_id]
    await callback.message.edit_text("❌ Оплата отменена", reply_markup=main_menu())
    await callback.answer()

# --- Поддержка ---
@dp.callback_query_handler(lambda c: c.data == "support")
async def support(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📞 *Напишите ваше сообщение*\n\n"
        "Просто отправьте текст, и администраторы ответят вам:",
        parse_mode="Markdown"
    )
    temp_payments[callback.from_user.id] = {"status": "support_wait"}
    await callback.answer()

@dp.message_handler(lambda msg: msg.from_user.id in temp_payments and temp_payments.get(msg.from_user.id, {}).get("status") == "support_wait")
async def forward_to_admins(message: types.Message):
    user = message.from_user
    text = f"📞 *Новое обращение*\n"
    text += f"👤 ID: `{user.id}`\n"
    text += f"📛 Имя: {user.first_name}\n"
    text += f"🔗 Username: @{user.username}\n\n"
    text += f"💬 Сообщение:\n{message.text}"
    
    for admin_id in ADMINS:
        await bot.send_message(admin_id, text, parse_mode="Markdown")
    
    await message.answer("✅ Сообщение отправлено администраторам. Ожидайте ответа.")
    del temp_payments[message.from_user.id]

# --- Ответ админа ---
import re
@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and msg.reply_to_message)
async def reply_to_user(message: types.Message):
    reply_text = message.reply_to_message.text or ""
    match = re.search(r"👤 ID: `(\d+)`", reply_text)
    if match:
        user_id = int(match.group(1))
        await bot.send_message(user_id, f"📞 *Ответ администратора:*\n\n{message.text}", parse_mode="Markdown")
        await message.answer("✅ Ответ отправлен пользователю")
    else:
        await message.answer("❌ Ответьте на сообщение из обращения")

# --- АДМИН-ПАНЕЛЬ ---
@dp.message_handler(commands=["admin"])
async def admin_cmd(message: types.Message):
    if message.from_user.id not in ADMINS:
        return
    await message.answer("🔧 *Панель администратора*", parse_mode="Markdown", reply_markup=admin_panel())

@dp.callback_query_handler(lambda c: c.data == "admin_prices")
async def admin_edit_prices(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return
    await callback.message.answer(
        "💰 *Редактирование цен*\n\n"
        "Введите 4 цены через пробел:\n"
        "`1день 7дней 30дней навсегда`\n"
        "Пример: `100 500 1500 5000`",
        parse_mode="Markdown"
    )
    temp_payments[callback.from_user.id] = {"status": "waiting_prices"}
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_add_keys")
async def admin_add_keys(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return
    await callback.message.answer(
        "🔑 *Добавление ключей*\n\n"
        "Введите: `тариф ключ`\n"
        "Тарифы: `1day`, `7day`, `30day`, `forever`\n"
        "Пример: `1day ABC123-xyz`\n\n"
        "Для завершения введите `готово`",
        parse_mode="Markdown"
    )
    temp_payments[callback.from_user.id] = {"status": "waiting_keys"}
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return
    keys = load_keys()
    users = load_users()
    text = "📊 *Статистика:*\n\n"
    text += f"👥 Пользователей: {len(users)}\n\n"
    text += "*Ключи в наличии:*\n"
    for tarif, key_list in keys.items():
        emoji = {"1day": "💎", "7day": "🔥", "30day": "⚡", "forever": "👑"}.get(tarif, "📦")
        text += f"{emoji} {tarif}: {len(key_list)} шт.\n"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_panel())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_mailing")
async def admin_mailing(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return
    await callback.message.answer("📢 Введите текст для рассылки (можно с Markdown):")
    temp_payments[callback.from_user.id] = {"status": "waiting_mailing"}
    await callback.answer()

# --- Обработка ввода админов ---
@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and temp_payments.get(msg.from_user.id, {}).get("status") == "waiting_prices")
async def save_prices(message: types.Message):
    parts = message.text.split()
    if len(parts) != 4 or not all(p.isdigit() for p in parts):
        await message.answer("❌ Введите 4 числа через пробел.")
        return
    data = load_data()
    data["prices"] = {
        "1day": int(parts[0]),
        "7day": int(parts[1]),
        "30day": int(parts[2]),
        "forever": int(parts[3])
    }
    save_data(data)
    await message.answer("✅ Цены обновлены!", reply_markup=admin_panel())
    del temp_payments[message.from_user.id]

@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and temp_payments.get(msg.from_user.id, {}).get("status") == "waiting_keys")
async def save_keys_admin(message: types.Message):
    if message.text.lower() == "готово":
        await message.answer("✅ Ключи сохранены!", reply_markup=admin_panel())
        del temp_payments[message.from_user.id]
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2 or parts[0] not in ["1day", "7day", "30day", "forever"]:
        await message.answer("❌ Формат: `тариф ключ`")
        return
    tarif, key = parts
    add_key(tarif, key)
    await message.answer(f"✅ Ключ добавлен для {tarif}\nОсталось: {len(load_keys()[tarif])}")
    await message.answer("Введите следующий ключ или `готово`")

@dp.message_handler(lambda msg: msg.from_user.id in ADMINS and temp_payments.get(msg.from_user.id, {}).get("status") == "waiting_mailing")
async def send_mailing(message: types.Message):
    users = load_users()
    success = 0
    fail = 0
    await message.answer(f"⏳ Рассылка для {len(users)} пользователей...")
    for user_id in users:
        try:
            await bot.send_message(user_id, message.text, parse_mode="Markdown")
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    await message.answer(f"✅ Готово!\n✅ Успешно: {success}\n❌ Ошибок: {fail}", reply_markup=admin_panel())
    del temp_payments[message.from_user.id]

# --- Запуск ---
if __name__ == "__main__":
    start_polling(dp, skip_updates=True)
