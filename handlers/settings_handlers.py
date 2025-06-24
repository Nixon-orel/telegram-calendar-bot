from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import config
from .common import CHOOSING_ACTION, CHOOSING_TIMEZONE, get_user_current_time, set_user_timezone

# Показать выбор часового пояса
async def show_timezone_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = []
    
    # Создаем кнопки для каждого доступного часового пояса
    for tz in config.AVAILABLE_TIMEZONES:
        keyboard.append([InlineKeyboardButton(tz, callback_data=f"tz_{tz}")])
    
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="Выберите ваш часовой пояс:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_TIMEZONE

# Установка часового пояса
async def set_timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    timezone = query.data.split("_", 1)[1]
    user_id = update.effective_user.id
    
    # Сохраняем часовой пояс пользователя
    set_user_timezone(user_id, timezone)
    
    # Получаем текущее время в выбранном часовом поясе
    now = get_user_current_time(user_id)
    formatted_date = now.strftime("%d.%m.%Y")
    formatted_time = now.strftime("%H:%M:%S")
    
    keyboard = [[InlineKeyboardButton("Назад в главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"Часовой пояс установлен: {timezone}\n\nТекущая дата: {formatted_date}\nТекущее время: {formatted_time}",
        reply_markup=reply_markup
    )
    
    return CHOOSING_ACTION