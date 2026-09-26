import os
import logging
import asyncio
import random
from flask import Flask, request

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== НАСТРОЙКИ БОТА ====================
TOKEN = "8916692361:AAGu2uVFdULLy0tiXlpj5uAuWCRWxaw0sI4"
ADMIN_ID = 1989967878

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# ==================== РЕКВИЗИТЫ ДЛЯ СБП ====================
# Укажите ваши реальные данные (можно менять и через Админ-панель)
PAYMENT_INFO = {
    "phone": "+7 (900) 000-00-00",
    "bank": "Т-Банк / Сбербанк",
    "recipient": "Иван И."
}

# ==================== КАТЕГОРИИ И ТОВАРЫ ====================
CATEGORIES = {
    "cat_ps": {"name": "🕹 PlayStation (PS4/PS5)", "icon": "🕹"},
    "cat_xbox": {"name": "🎮 Xbox", "icon": "🎮"},
    "cat_ai": {"name": "🤖 ИИ Инструменты", "icon": "🤖"},
    "cat_music": {"name": "🎵 Музыка & Сервисы", "icon": "🎵"}
}

PRODUCTS = {
    "p_ps_plus": {
        "cat_id": "cat_ps",
        "name": "PlayStation Plus Deluxe / Extra",
        "image": "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?w=800",
        "desc": "⚡️ **Полный доступ к сотням игр на PS4 и PS5.**\n\nВключает онлайн-мультиплеер, каталог из 400+ игр и эксклюзивные скидки.",
        "variants": {
            "1m": {"label": "1 месяц", "price": 850},
            "3m": {"label": "3 месяца", "price": 2100},
            "6m": {"label": "6 месяцев", "price": 3800},
            "12m": {"label": "12 месяцев", "price": 6490}
        }
    },
    "p_xbox_pass": {
        "cat_id": "cat_xbox",
        "name": "Xbox Game Pass Ultimate",
        "image": "https://images.unsplash.com/photo-1621252179027-945198901061?w=800",
        "desc": "🎮 **Максимальная подписка для Xbox и ПК!**\n\nВключает Game Pass, EA Play и облачный гейминг.",
        "variants": {
            "1m": {"label": "1 месяц", "price": 790},
            "3m": {"label": "3 месяца", "price": 2190},
            "12m": {"label": "12 месяцев", "price": 5990}
        }
    },
    "p_chatgpt": {
        "cat_id": "cat_ai",
        "name": "ChatGPT Plus (GPT-4o)",
        "image": "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=800",
        "desc": "🚀 **Доступ к передовому ИИ.** Скорость, приоритетный доступ, генерация DALL-E 3 и анализ файлов.",
        "variants": {
            "1m": {"label": "1 месяц", "price": 2390}
        }
    },
    "p_spotify": {
        "cat_id": "cat_music",
        "name": "Spotify Premium Individual",
        "image": "https://images.unsplash.com/photo-1614680376593-902f749f71c3?w=800",
        "desc": "🎧 **Музыка без рекламы в высоком качестве.** Возможность офлайн-скачивания.",
        "variants": {
            "1m": {"label": "1 месяц", "price": 350},
            "3m": {"label": "3 месяца", "price": 950},
            "12m": {"label": "12 месяцев", "price": 2890}
        }
    }
}

ORDERS = {}

class AdminStates(StatesGroup):
    add_prod_cat = State()
    add_prod_name = State()
    add_prod_desc = State()
    add_prod_img = State()
    add_prod_prices = State()
    edit_sbp_phone = State()
    edit_sbp_bank = State()
    edit_sbp_name = State()
    waiting_for_key = State()

# ==================== ОТОБРАЖЕНИЕ МЕНЮ И КАТАЛОГА ====================
async def show_main_menu(message_or_callback, user_id: int):
    keyboard = []
    for cat_id, cat in CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(text=f"{cat['icon']} {cat['name']}", callback_data=f"show_cat_{cat_id}")])
    
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton(text="⚙️ Панель Администратора", callback_data="admin_panel")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    text = "💎 **Добро пожаловать в Магазин Подписок!**\n\nВыберите интересующий раздел:"

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=markup, parse_mode="Markdown")
    else:
        try:
            await message_or_callback.message.delete()
        except Exception:
            pass
        await message_or_callback.message.answer(text, reply_markup=markup, parse_mode="Markdown")

@dp.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await show_main_menu(message, message.from_user.id)

@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main_menu(callback, callback.from_user.id)
    await callback.answer()

@dp.callback_query(F.data.startswith("show_cat_"))
async def show_category_products(callback: CallbackQuery):
    cat_id = callback.data.replace("show_cat_", "")
    cat = CATEGORIES.get(cat_id)
    if not cat:
        return

    keyboard = []
    for p_id, p_data in PRODUCTS.items():
        if p_data.get("cat_id") == cat_id:
            min_price = min(v["price"] for v in p_data["variants"].values())
            keyboard.append([InlineKeyboardButton(
                text=f"{p_data['name']} — от {min_price} ₽",
                callback_data=f"show_prod_{p_id}"
            )])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="main_menu")])
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(f"📂 **Раздел:** {cat['name']}\n\nВыберите подписку:", reply_markup=markup, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("show_prod_"))
async def show_product_card(callback: CallbackQuery):
    p_id = callback.data.replace("show_prod_", "")
    prod = PRODUCTS.get(p_id)
    if not prod:
        return

    keyboard = []
    # Кнопки выбора периода с ценой
    for v_key, v_data in prod["variants"].items():
        keyboard.append([InlineKeyboardButton(
            text=f"🗓 {v_data['label']} — {v_data['price']} руб.",
            callback_data=f"buy_{p_id}_{v_key}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад к разделу", callback_data=f"show_cat_{prod['cat_id']}")])
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    caption_text = f"🌟 **{prod['name']}**\n\n{prod['desc']}\n\n👇 **Выберите период подписки:**"

    try:
        await callback.message.delete()
    except Exception:
        pass

    try:
        await callback.message.answer_photo(photo=prod["image"], caption=caption_text, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(caption_text, reply_markup=markup, parse_mode="Markdown")

    await callback.answer()

# ==================== ВЫБОР ПЕРИОДА И СЧЕТ НА ОПЛАТУ СБП ====================
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy_variant(callback: CallbackQuery):
    parts = callback.data.split("_")
    p_id = parts[1]
    v_key = parts[2]

    prod = PRODUCTS.get(p_id)
    if not prod or v_key not in prod["variants"]:
        await callback.answer("Ошибка выбора периода", show_alert=True)
        return

    variant = prod["variants"][v_key]
    order_id = f"ORD-{random.randint(10000, 99999)}"

    # Сохраняем данные заказа
    ORDERS[order_id] = {
        "user_id": callback.from_user.id,
        "username": callback.from_user.username,
        "full_name": callback.from_user.full_name,
        "product_name": prod["name"],
        "variant_label": variant["label"],
        "price": variant["price"]
    }

    # Диплинк для быстрого открытия СБП в приложении банка
    phone_clean = PAYMENT_INFO['phone'].replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
    sbp_link = f"https://qr.nspk.ru/pay?type=01&bank=100000000004&sum={variant['price']}&phone={phone_clean}&cur=RUB&text={order_id}"

    pay_text = (
        f"🧾 **СЧЕТ НА ОПЛАТУ СБП #{order_id}**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📦 **Товар:** {prod['name']}\n"
        f"⏳ **Период:** {variant['label']}\n"
        f"💰 **Сумма к оплате:** `{variant['price']} RUB`\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 **Реквизиты для перевода по СБП:**\n"
        f"📱 **Номер:** `{PAYMENT_INFO['phone']}`\n"
        f"🏦 **Банк:** {PAYMENT_INFO['bank']}\n"
        f"👤 **Получатель:** {PAYMENT_INFO['recipient']}\n\n"
        f"⚠️ **ВАЖНО:** В комментарии к переводу укажите: **{order_id}**\n\n"
        f"После совершения перевода нажмите кнопку **«✅ Я оплатил(а)»** ниже."
    )

    keyboard = [
        [InlineKeyboardButton(text="📲 Оплатить через СБП (в приложении)", url=sbp_link)],
        [InlineKeyboardButton(text="✅ Я оплатил(а)", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(pay_text, reply_markup=markup, parse_mode="Markdown")
    await callback.answer()

# ==================== ОПЛАТА И УВЕДОМЛЕНИЕ АДМИНИСТРАТОРУ ====================
@dp.callback_query(F.data.startswith("paid_"))
async def user_confirm_payment(callback: CallbackQuery):
    order_id = callback.data.replace("paid_", "")
    order = ORDERS.get(order_id)

    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    # 1. Шаблонное сообщение покупателю
    client_text = (
        f"🚀 **Заказ #{order_id} успешно принят в обработку!**\n\n"
        f"Менеджер проверяет поступление средств. В течение **10 минут** вы получите данные подписки и инструкцию по активации прямо в этот чат Telegram.\n\n"
        f"Спасибо за покупку! ❤️"
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(client_text, parse_mode="Markdown")

    # 2. Подробное уведомление Администратору с кликабельной ссылкой на профиль
    user_link = f"@{order['username']}" if order['username'] else f"[Профиль](tg://user?id={order['user_id']})"
    
    admin_notice = (
        f"🔥 **НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ #{order_id}**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Покупатель:** {order['full_name']} ({user_link})\n"
        f"🆔 **ID Клиента:** `{order['user_id']}`\n"
        f"📦 **Товар:** {order['product_name']}\n"
        f"⏳ **Срок:** {order['variant_label']}\n"
        f"💵 **Сумма:** `{order['price']} RUB`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Проверьте приход в банке и нажмите кнопку ниже для выдачи:"
    )

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Выдать товар / код клиенту", callback_data=f"fulfill_{order_id}")]
    ])

    await bot.send_message(ADMIN_ID, admin_notice, reply_markup=admin_kb, parse_mode="Markdown")
    await callback.answer()

# ==================== РУЧНАЯ ВЫДАЧА КОДА/ДАННЫХ АДМИНОМ ====================
@dp.callback_query(F.data.startswith("fulfill_"))
async def start_fulfill(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    order_id = callback.data.replace("fulfill_", "")
    order = ORDERS.get(order_id)

    if not order:
        await callback.answer("Заказ не найден в памяти", show_alert=True)
        return

    await state.update_data(fulfill_order_id=order_id)
    await callback.message.answer(
        f"✍️ **Введите код активации / логин и пароль для заказа #{order_id}:**\n\n"
        f"Отправьте текст следующим сообщением, и бот мгновенно перешлет его покупателю.",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_key)
    await callback.answer()

@dp.message(AdminStates.waiting_for_key)
async def process_fulfill_send(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    data = await state.get_data()
    order_id = data.get("fulfill_order_id")
    order = ORDERS.get(order_id)

    if order:
        delivery_text = (
            f"🎁 **ВАШ ЗАКАЗ #{order_id} ГОТОВ!**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📦 **Товар:** {order['product_name']} ({order['variant_label']})\n\n"
            f"🔑 **Данные доступа / Активация:**\n"
            f"`{message.text}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Приятного пользования! По всем вопросам пишите нашей поддержке."
        )
        try:
            await bot.send_message(order['user_id'], delivery_text, parse_mode="Markdown")
            await message.answer(f"✅ **Данные успешно отправлены покупателю (ID: {order['user_id']})!**", parse_mode="Markdown")
        except Exception as e:
            await message.answer(f"❌ Ошибка отправки: {e}")

    await state.clear()

# ==================== АДМИН-ПАНЕЛЬ И НАСТРОЙКИ РЕКВИЗИТОВ ====================
@dp.callback_query(F.data == "admin_panel")
async def admin_panel_main(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="adm_add_prod_start")],
        [InlineKeyboardButton(text="💳 Изменить реквизиты СБП", callback_data="adm_edit_sbp")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])
    
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer("⚙️ **ПАНЕЛЬ УПРАВЛЕНИЯ МАГАЗИНОМ**", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "adm_edit_sbp")
async def edit_sbp_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите **номер телефона** для СБП (например, `+79001234567`):", parse_mode="Markdown")
    await state.set_state(AdminStates.edit_sbp_phone)
    await callback.answer()

@dp.message(AdminStates.edit_sbp_phone)
async def edit_sbp_phone(message: Message, state: FSMContext):
    PAYMENT_INFO["phone"] = message.text
    await message.answer("Введите **название банка** (например, *Т-Банк / Сбер*):", parse_mode="Markdown")
    await state.set_state(AdminStates.edit_sbp_bank)

@dp.message(AdminStates.edit_sbp_bank)
async def edit_sbp_bank(message: Message, state: FSMContext):
    PAYMENT_INFO["bank"] = message.text
    await message.answer("Введите **Имя Получателя** (например, *Иван И.*):", parse_mode="Markdown")
    await state.set_state(AdminStates.edit_sbp_name)

@dp.message(AdminStates.edit_sbp_name)
async def edit_sbp_name(message: Message, state: FSMContext):
    PAYMENT_INFO["recipient"] = message.text
    await message.answer("✅ **Реквизиты СБП успешно обновлены!**", parse_mode="Markdown")
    await state.clear()

# ==================== FLASK SERVER ДЛЯ RENDER ====================
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
    return "Sub Bot is Active!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
