import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from flask import Flask, request

# --- ВАШИ АКТУАЛЬНЫЕ ДАННЫЕ ---
TOKEN = "8916692361:AAGu2uVFdULLy0tiXlpj5uAuWCRWxaw0sI4"
ADMIN_ID = 1989967878

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# База данных товаров
PRODUCTS = {
    "1": {"name": "YouTube Premium (1 мес)", "price": 300, "desc": "Официальная подписка на месяц"},
    "2": {"name": "Spotify (3 месяца)", "price": 450, "desc": "Индивидуальный аккаунт"}
}
ORDERS = {}

class AdminStates(StatesGroup):
    add_name = State()
    add_price = State()
    add_desc = State()
    waiting_for_key = State()

@dp.message(lambda message: message.text == "/start")
async def cmd_start(message: Message):
    keyboard = []
    for p_id, p_data in PRODUCTS.items():
        keyboard.append([InlineKeyboardButton(
            text=f"{p_data['name']} — {p_data['price']} руб.", 
            callback_data=f"buy_{p_id}"
        )])
    
    if message.from_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton(text="⚙️ Панель администратора", callback_data="admin_panel")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(
        "👋 **Добро пожаловать в наш магазин подписок!**\nВыберите нужный товар из каталога ниже:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    p_id = callback.data.replace("buy_", "")
    product = PRODUCTS.get(p_id)
    
    if not product:
        await callback.answer("Товар не найден!", show_alert=True)
        return

    order_id = str(len(ORDERS) + 101)
    ORDERS[order_id] = {"user_id": callback.from_user.id, "product": product['name']}

    payment_text = (
        f"🛒 **Ваш заказ №{order_id}**\n"
        f"📦 Товар: *{product['name']}*\n"
        f"📝 Описание: {product['desc']}\n"
        f"💰 К оплате: *{product['price']} руб.*\n\n"
        f"💳 **Как оплатить:**\n"
        f"Переведите сумму по номеру СБП: `+79000000000` (Банк / Имя)\n"
        f"В комментарии к переводу обязательно укажите номер заказа: **{order_id}**\n\n"
        f"После оплаты нажмите кнопку ниже, чтобы уведомить администратора."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил(а) заказ", callback_data=f"paid_{order_id}")]
    ])
    
    await callback.message.answer(payment_text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("paid_"))
async def user_paid(callback: CallbackQuery):
    order_id = callback.data.replace("paid_", "")
    order_info = ORDERS.get(order_id)
    
    await callback.message.answer("⏳ Спасибо! Информация отправлена администратору. Ожидайте выдачи товара (обычно 5-15 минут).")
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Выдать ключ клиенту", callback_data=f"sendkey_{order_info['user_id']}")]
    ])
    
    await bot.send_message(
        ADMIN_ID,
        f"🚨 **НОВАЯ ОПЛАТА / ЗАКАЗ №{order_id}**\n\n"
        f"Товар: *{order_info['product']}*\n"
        f"Клиент ID: `{order_info['user_id']}`\n"
        f"Проверьте поступление денег и нажмите кнопку для выдачи ключа.",
        reply_markup=admin_kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="adm_add")],
        [InlineKeyboardButton(text="🗑 Удалить товар", callback_data="adm_del_list")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="adm_back")]
    ])
    await callback.message.edit_text("⚙️ **Панель управления магазином:**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "adm_back")
async def adm_back(callback: CallbackQuery):
    await callback.message.delete()
    await cmd_start(callback.message)

@dp.callback_query(lambda c: c.data == "adm_del_list")
async def adm_del_list(callback: CallbackQuery):
    kb = []
    for p_id, p_data in PRODUCTS.items():
        kb.append([InlineKeyboardButton(text=f"❌ Удалить: {p_data['name']}", callback_data=f"del_{p_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    
    await callback.message.edit_text("Выберите товар для удаления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(lambda c: c.data.startswith("del_"))
async def adm_delete_product(callback: CallbackQuery):
    p_id = callback.data.replace("del_", "")
    if p_id in PRODUCTS:
        del PRODUCTS[p_id]
        await callback.answer("Товар успешно удален!", show_alert=True)
    await admin_panel(callback)

@dp.callback_query(lambda c: c.data == "adm_add")
async def adm_add_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите **название** нового товара (например: *Netflix 1 месяц*):", parse_mode="Markdown")
    await state.set_state(AdminStates.add_name)
    await callback.answer()

@dp.message(AdminStates.add_name)
async def adm_add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите **стоимость** товара в рублях (только цифры, например: *500*):")
    await state.set_state(AdminStates.add_price)

@dp.message(AdminStates.add_price)
async def adm_add_price(message: Message, state: FSMContext):
    await state.update_data(price=int(message.text))
    await message.answer("Введите **описание** товара:")
    await state.set_state(AdminStates.add_desc)

@dp.message(AdminStates.add_desc)
async def adm_add_desc(message: Message, state: FSMContext):
    data = await state.get_data()
    new_id = str(len(PRODUCTS) + 1)
    
    PRODUCTS[new_id] = {
        "name": data['name'],
        "price": data['price'],
        "desc": message.text
    }
    
    await message.answer("✅ **Товар успешно добавлен в витрину!** Теперь он виден пользователям в /start.", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("sendkey_"))
async def admin_click_sendkey(callback: CallbackQuery, state: FSMContext):
    target_user_id = callback.data.replace("sendkey_", "")
    await state.update_data(target_user=target_user_id)
    await callback.message.answer("✍️ Введите текстом ключ, данные от аккаунта или инструкцию для отправки покупателю:")
    await state.set_state(AdminStates.waiting_for_key)
    await callback.answer()

@dp.message(AdminStates.waiting_for_key)
async def send_key_to_user(message: Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("target_user")
    key_text = message.text
    
    try:
        await bot.send_message(
            target_user_id,
            f"🎁 **Ваш заказ готов! Вот данные для доступа:**\n\n{key_text}\n\nСпасибо за покупку! Пожалуйста, оставьте отзыв."
        )
        await message.answer("✅ Ключ успешно доставлен покупателю!")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки (возможно, клиент заблокировал бота): {e}")
        
    await state.clear()

# --- ВЕБХУК ДЛЯ FLASK ---

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_data = request.get_json()
        update = types.Update.model_validate(json_data, context={"bot": bot})
        asyncio.run(dp.feed_update(bot=bot, update=update))
        return "OK", 200
    else:
        return "Invalid content type", 403

@app.route('/')
def index():
    return "Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
