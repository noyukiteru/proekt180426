import re
from datetime import datetime

import httpx
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from bot.api_client import (
    get_services, get_masters, create_appointment,
    get_user_appointments, cancel_appointment, create_review
)

router = Router()
API_BASE = "http://127.0.0.1:8000/api"

# Состояния 
class BookingState(StatesGroup):
    picking_service = State()
    picking_master = State()
    picking_date = State()
    picking_time = State()
    rescheduling_time = State()  # Новое состояние для переноса

class ReviewState(StatesGroup):
    waiting_rating = State()
    waiting_comment = State()


async def get_or_create_user(telegram_id: str, name: str) -> int:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:

            resp = await client.post(
                f"{API_BASE}/users/",
                json={"telegram_id": telegram_id, "name": name, "phone": ""}
            )
            resp.raise_for_status()
            return resp.json()["id"]
        except Exception:

            return 1

# ГЛАВНОЕ МЕНЮ
@router.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Записаться", callback_data="menu_book")],
        [InlineKeyboardButton(text="📋 Мои записи", callback_data="menu_my_apps")],
        [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="menu_review")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help")]
    ])
    await message.answer(
        "👋 *Добро пожаловать в шиномонтаж!*\n\nВыберите действие:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_help")
async def show_help(callback: CallbackQuery):
    help_text = (
        "📖 *Инструкция:*\n"
        "1️⃣ Записаться — выберите услугу, мастера и время\n"
        "2️⃣ Мои записи — просмотр и управление\n"
        "3️⃣ Отзыв — оценка после визита\n\n"
        "📞 Контакты:\n📍 ул. Примерная, 123\n⏰ 9:00-20:00"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back")]])
    await callback.message.answer(help_text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "menu_back")
async def go_back(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await cmd_start(callback.message)
    await callback.answer()

# ЗАПИСЬ
@router.callback_query(F.data == "menu_book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    services = await get_services()
    if not services:
        await callback.answer("⚠️ Каталог услуг пуст", show_alert=True)
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{s['title']} - {s['price']}₽", callback_data=f"svc_{s['id']}")]
        for s in services
    ])
    
    await callback.message.answer("🔧 *Выберите услугу:*", reply_markup=kb, parse_mode="Markdown")
    await state.set_state(BookingState.picking_service)
    await callback.answer()

@router.callback_query(BookingState.picking_service, F.data.startswith("svc_"))
async def process_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    await state.update_data(service_id=service_id)
    
    masters = await get_masters()
    active_masters = [m for m in masters if m.get('is_active', True)]
    
    if not active_masters:
        await callback.answer("⚠️ Нет доступных мастеров", show_alert=True)
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m['name'], callback_data=f"mstr_{m['id']}")]
        for m in active_masters
    ])
    
    await callback.message.answer("👨‍🔧 *Выберите мастера:*", reply_markup=kb, parse_mode="Markdown")
    await state.set_state(BookingState.picking_master)
    await callback.answer()

@router.callback_query(BookingState.picking_master, F.data.startswith("mstr_"))
async def process_master(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[1])
    await state.update_data(master_id=master_id)
    
    # Переходим к выбору ДАТЫ
    await state.set_state(BookingState.picking_date)
    
    await callback.message.answer(
        "📅 *Введите желаемую дату:*\n"
        "Формат: `ГГГГ-ММ-ДД`\n"
        "Пример: `2024-12-01`",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(BookingState.picking_time)
async def process_time(message: Message, state: FSMContext):
    date_time = message.text.strip()
    if not re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', date_time):
        await message.answer("⚠️ Неверный формат!\nИспользуйте: `YYYY-MM-DD HH:MM`\nПример: `2024-12-01 14:30`", parse_mode="Markdown")
        return
    
    data = await state.get_data()
    # ID пользователя
    user_id = await get_or_create_user(str(message.from_user.id), message.from_user.full_name or "Клиент")
    
    try:
        result = await create_appointment(
            user_id=user_id,
            master_id=data['master_id'],
            service_id=data['service_id'],
            date_time=date_time
        )
        await message.answer(
            f"✅ *Запись создана!*\n\n"
            f"🎫 Талон: #{result.get('id')}\n"
            f"📅 Время: {date_time}\n"
            f"🔹 Статус: {result.get('status', 'pending')}",
            parse_mode="Markdown"
        )
    except Exception as e:
        err_msg = str(e)
        if "409" in err_msg or "занято" in err_msg.lower():
            await message.answer("⛔ Это время уже занято! Выберите другой слот.")
        else:
            await message.answer(f"⚠️ Ошибка сервера: {err_msg}")
    
    await state.clear()

# МОИ ЗАПИСИ
@router.callback_query(F.data == "menu_my_apps")
async def show_my_appointments(callback: CallbackQuery):
    apps = await get_user_appointments(str(callback.from_user.id))
    if not apps:
        await callback.answer("📭 У вас нет активных записей", show_alert=True)
        return
    
    for app in apps:
        status_emoji = {"pending": "⏳", "confirmed": "✅", "completed": "🏁", "cancelled": "❌"}
        status = status_emoji.get(app["status"], "❓")
        
        text = f"{status} *Запись #{app['id']}*\n📅 {app['date_time']}\n🔹 Статус: {app['status']}"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{app['id']}")],
            [InlineKeyboardButton(text="🔄 Перенести", callback_data=f"reschedule_{app['id']}")]
        ])
        
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    
    await callback.answer()

@router.callback_query(F.data.startswith("cancel_"))
async def process_cancel(callback: CallbackQuery):
    app_id = int(callback.data.split("_")[1])
    if await cancel_appointment(app_id):
        await callback.message.edit_text(f"✅ Запись #{app_id} отменена!")
    else:
        await callback.answer("❌ Не удалось отменить", show_alert=True)
    await callback.answer()

@router.callback_query(F.data.startswith("reschedule_"))
async def start_reschedule(callback: CallbackQuery, state: FSMContext):
    app_id = int(callback.data.split("_")[1])
    await state.update_data(app_id=app_id)
    await state.set_state(BookingState.rescheduling_time)
    
    await callback.message.answer("📅 *Введите НОВОЕ время:*\nФормат: `YYYY-MM-DD HH:MM`", parse_mode="Markdown")
    await callback.answer()

@router.message(BookingState.rescheduling_time)
async def process_reschedule_time(message: Message, state: FSMContext):
    date_time = message.text.strip()
    if not re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', date_time):
        await message.answer("⚠️ Неверный формат времени!", parse_mode="Markdown")
        return
    
    data = await state.get_data()
    app_id = data.get('app_id')
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(f"{API_BASE}/appointments/{app_id}", json={"date_time": date_time})
            resp.raise_for_status()
        
        await message.answer(f"✅ Запись #{app_id} перенесена на {date_time}!")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка переноса: {e}")
    
    await state.clear()

# ОТЗЫВЫ
@router.callback_query(F.data == "menu_review")
async def start_review(callback: CallbackQuery, state: FSMContext):
    apps = await get_user_appointments(str(callback.from_user.id))
    completed = [a for a in apps if a.get('status') == 'completed']
    
    if not completed:
        await callback.answer("📭 Нет завершённых записей для отзыва", show_alert=True)
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Запись #{a['id']}", callback_data=f"review_{a['id']}")]
        for a in completed[:5]
    ])
    
    await callback.message.answer("⭐ *Выберите запись для отзыва:*", reply_markup=kb, parse_mode="Markdown")
    await state.set_state(ReviewState.waiting_rating)
    await callback.answer()

@router.callback_query(ReviewState.waiting_rating, F.data.startswith("review_"))
async def process_review_select(callback: CallbackQuery, state: FSMContext):
    app_id = int(callback.data.split("_")[1])
    await state.update_data(app_id=app_id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{i} ⭐" * i, callback_data=f"rate_{i}")]
        for i in range(1, 6)
    ])
    
    await callback.message.answer("⭐ *Оцените от 1 до 5:*", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(ReviewState.waiting_rating, F.data.startswith("rate_"))
async def process_rating(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split("_")[1])
    await state.update_data(rating=rating)
    await callback.message.answer("💬 *Напишите комментарий:*")
    await state.set_state(ReviewState.waiting_comment)
    await callback.answer()

@router.message(ReviewState.waiting_comment)
async def process_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    if await create_review(data['app_id'], data['rating'], message.text):
        await message.answer("✅ *Спасибо за отзыв!*", parse_mode="Markdown")
    else:
        await message.answer("⚠️ Ошибка при отправке отзыва")
    await state.clear()
    
@router.message(BookingState.picking_date)
async def process_date(message: Message, state: FSMContext):
    date_text = message.text.strip()
    
    # Простая проверка формата
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        await message.answer("⚠️ Неверный формат даты. Используйте `2024-12-01`")
        return

    await state.update_data(date=date_text)
    data = await state.get_data()
    
    # 🔥 Запрашиваем слоты у сервера
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            # Запрос к нашему новому эндпоинту
            resp = await client.get(
                f"http://127.0.0.1:8000/api/appointments/slots/",
                params={
                    "master_id": data['master_id'],
                    "service_id": data['service_id'],
                    "date": date_text
                }
            )
            slots = resp.json()
        
        if not slots:
            await message.answer("😔 К сожалению, на эту дату свободных окон нет. Попробуйте другую дату.")
            # Можно здесь перезапустить FSM на ввод даты
            return
            
        # Формируем кнопки
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=f"time_{t}")]
            for t in slots
        ])
        
        await message.answer("⏰ *Выберите свободное время:*", reply_markup=kb, parse_mode="Markdown")
        await state.set_state(BookingState.picking_time) # Переходим в ожидание выбора времени
        
    except Exception as e:
        await message.answer(f"⚠️ Ошибка получения расписания: {e}")
@router.callback_query(BookingState.picking_time, F.data.startswith("time_"))
async def process_time_selection(callback: CallbackQuery, state: FSMContext):
    selected_time = callback.data.split("_")[1] # Получаем "10:30"
    
    data = await state.get_data()
    date = data['date']
    date_time_str = f"{date} {selected_time}" # Собираем "2024-12-01 10:30"
    
    # Создаем запись через API (как было раньше)
    try:
        # ... (ваш код create_appointment здесь) ...
        # Вызовите вашу функцию из api_client.py или напрямую запрос к серверу
        result = await create_appointment(
            user_id=1, # Замените на реальную логику ID пользователя
            master_id=data['master_id'],
            service_id=data['service_id'],
            date_time=date_time_str
        )
        
        await callback.message.answer(f"✅ *Запись подтверждена!*\n\n🎫 Талон: #{result['id']}\n📅 {date_time_str}")
        
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при бронировании: {e}")
        
    await state.clear()
    await callback.answer()