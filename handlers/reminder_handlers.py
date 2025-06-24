import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database
from .common import (
    CHOOSING_ACTION, CHOOSING_EVENT_FOR_REMINDER, ADDING_REMINDER_DATE,
    ADDING_REMINDER_TIME, CHOOSING_REMINDER_TO_DELETE, CONFIRMING_REMINDER_DELETION,
    show_main_menu
)

# Выбор события для напоминания
async def choose_event_for_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Обработка случая, когда пользователь выбрал "Да" после создания события
    if query.data == "add_reminder_now":
        event_id = context.user_data.get("event_id")
        if not event_id:
            await query.edit_message_text(text="Ошибка: событие не найдено.")
            return await show_main_menu(update, context)
    else:
        # Обычный случай выбора события из списка
        event_id = int(query.data.split("_")[1])
        context.user_data["event_id"] = event_id
        
        # Получаем информацию о событии
        event = database.get_event(event_id)
        
        if event:
            name, date, time = event
            context.user_data["event_name"] = name
            context.user_data["event_date"] = date
            context.user_data["event_time"] = time
    
    await query.edit_message_text(
        text=f"Добавление напоминания для события '{context.user_data['event_name']}' ({context.user_data['event_date']} {context.user_data['event_time']}).\n\nВведите дату напоминания в формате ДД.ММ.ГГГГ:"
    )
    
    return ADDING_REMINDER_DATE

# Добавление даты напоминания
async def add_reminder_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reminder_date = update.message.text
    
    # Проверка формата даты
    try:
        datetime.datetime.strptime(reminder_date, "%d.%m.%Y")
        context.user_data["reminder_date"] = reminder_date
        
        await update.message.reply_text(
            "Введите время напоминания в формате ЧЧ:ММ:"
        )
        
        return ADDING_REMINDER_TIME
    except ValueError:
        await update.message.reply_text(
            "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ:"
        )
        return ADDING_REMINDER_DATE

# Добавление времени напоминания
async def add_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reminder_time = update.message.text
    
    # Проверка формата времени
    try:
        datetime.datetime.strptime(reminder_time, "%H:%M")
        context.user_data["reminder_time"] = reminder_time
        
        # Сохраняем напоминание в базу данных
        database.add_reminder(
            context.user_data["event_id"],
            context.user_data["reminder_date"],
            context.user_data["reminder_time"]
        )
        
        keyboard = [
            [InlineKeyboardButton("Добавить еще напоминание", callback_data=f"event_{context.user_data['event_id']}")],
            [InlineKeyboardButton("Вернуться в главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Напоминание для события '{context.user_data['event_name']}' добавлено на {context.user_data['reminder_date']} в {context.user_data['reminder_time']}.",
            reply_markup=reply_markup
        )
        
        return CHOOSING_EVENT_FOR_REMINDER
    except ValueError:
        await update.message.reply_text(
            "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ:"
        )
        return ADDING_REMINDER_TIME

# Показать список событий для удаления напоминаний
async def show_events_for_reminder_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    events = database.get_user_events_with_reminders(update.effective_user.id)
    
    if not events:
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text="У вас нет событий с напоминаниями.",
            reply_markup=reply_markup
        )
        return CHOOSING_ACTION
    
    keyboard = []
    for event in events:
        event_id, name, date, time = event
        keyboard.append([InlineKeyboardButton(f"{name} ({date} {time})", callback_data=f"delete_reminder_event_{event_id}")])
    
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="Выберите событие, для которого хотите удалить напоминание:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_EVENT_FOR_REMINDER

# Показать список напоминаний для удаления
async def show_reminders_for_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    event_id = int(query.data.split("_")[3])
    context.user_data["event_id_for_reminder_deletion"] = event_id
    
    # Получаем информацию о событии
    event = database.get_event(event_id)
    
    if not event:
        await query.edit_message_text(text="Событие не найдено.")
        return await show_main_menu(update, context)
    
    name, date, time = event
    context.user_data["event_name_for_reminder_deletion"] = name
    
    # Получаем напоминания для события
    reminders = database.get_event_reminders(event_id)
    
    if not reminders:
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"У события '{name}' нет напоминаний.",
            reply_markup=reply_markup
        )
        return CHOOSING_ACTION
    
    keyboard = []
    for reminder in reminders:
        reminder_id, reminder_date, reminder_time = reminder
        keyboard.append([InlineKeyboardButton(f"{reminder_date} в {reminder_time}", callback_data=f"delete_reminder_{reminder_id}")])
    
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"Выберите напоминание для события '{name}' ({date} {time}) для удаления:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_REMINDER_TO_DELETE

# Подтверждение удаления напоминания
async def confirm_reminder_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    reminder_id = int(query.data.split("_")[2])
    context.user_data["reminder_id_to_delete"] = reminder_id
    
    # Получаем информацию о напоминании
    reminder = database.get_reminder(reminder_id)
    
    if not reminder:
        await query.edit_message_text(text="Напоминание не найдено.")
        return await show_main_menu(update, context)
    
    reminder_date, reminder_time = reminder
    
    keyboard = [
        [InlineKeyboardButton("Да, удалить", callback_data=f"confirm_delete_reminder_{reminder_id}")],
        [InlineKeyboardButton("Нет, отменить", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    event_name = context.user_data.get("event_name_for_reminder_deletion", "")
    
    await query.edit_message_text(
        text=f"Вы уверены, что хотите удалить напоминание на {reminder_date} в {reminder_time} для события '{event_name}'?",
        reply_markup=reply_markup
    )
    
    return CONFIRMING_REMINDER_DELETION

# Удаление напоминания
async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    reminder_id = int(query.data.split("_")[3])
    
    # Удаляем напоминание
    database.delete_reminder(reminder_id)
    
    keyboard = [[InlineKeyboardButton("Назад в главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="Напоминание успешно удалено.",
        reply_markup=reply_markup
    )
    
    return CHOOSING_ACTION