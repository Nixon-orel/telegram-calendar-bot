import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database
from .common import (
    ADDING_EVENT_NAME, ADDING_EVENT_DATE, ADDING_EVENT_TIME, ADDING_REMINDER,
    CHOOSING_ACTION, CHOOSING_EVENT_TO_VIEW, CHOOSING_EVENT_TO_DELETE,
    CONFIRMING_EVENT_DELETION, CHOOSING_EVENT_FOR_REMINDER,
    show_main_menu
)

# Добавление названия события
async def add_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    event_name = update.message.text
    context.user_data["event_name"] = event_name
    
    await update.message.reply_text(
        "Введите дату события в формате ДД.ММ.ГГГГ:"
    )
    
    return ADDING_EVENT_DATE

# Добавление даты события
async def add_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    event_date = update.message.text
    
    # Проверка формата даты
    try:
        datetime.datetime.strptime(event_date, "%d.%m.%Y")
        context.user_data["event_date"] = event_date
        
        await update.message.reply_text(
            "Введите время события в формате ЧЧ:ММ:"
        )
        
        return ADDING_EVENT_TIME
    except ValueError:
        await update.message.reply_text(
            "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ:"
        )
        return ADDING_EVENT_DATE

# Добавление времени события
async def add_event_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    event_time = update.message.text
    
    # Проверка формата времени
    try:
        datetime.datetime.strptime(event_time, "%H:%M")
        context.user_data["event_time"] = event_time
        
        # Сохраняем событие в базу данных
        event_id = database.add_event(
            update.effective_user.id,
            context.user_data["event_name"],
            context.user_data["event_date"],
            context.user_data["event_time"]
        )
        
        context.user_data["event_id"] = event_id
        
        keyboard = [
            [InlineKeyboardButton("Да", callback_data="add_reminder_now")],
            [InlineKeyboardButton("Нет", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Событие '{context.user_data['event_name']}' добавлено на {context.user_data['event_date']} в {context.user_data['event_time']}.\n\nХотите добавить напоминание?",
            reply_markup=reply_markup
        )
        
        return ADDING_REMINDER
    except ValueError:
        await update.message.reply_text(
            "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ:"
        )
        return ADDING_EVENT_TIME

# Показать список событий
async def show_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    events = database.get_user_events(update.effective_user.id)
    
    if not events:
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text="У вас нет событий.",
            reply_markup=reply_markup
        )
        return CHOOSING_ACTION
    
    keyboard = []
    for event in events:
        event_id, name, date, time = event
        keyboard.append([InlineKeyboardButton(f"{name} ({date} {time})", callback_data=f"view_event_{event_id}")])
    
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="Ваши события:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_EVENT_TO_VIEW

# Просмотр деталей события
async def view_event_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    event_id = int(query.data.split("_")[2])
    
    # Получаем информацию о событии
    event = database.get_event(event_id)
    
    if not event:
        await query.edit_message_text(text="Событие не найдено.")
        return await show_main_menu(update, context)
    
    name, date, time = event
    
    # Получаем напоминания для события
    reminders = database.get_event_reminders(event_id)
    
    reminders_text = ""
    if reminders:
        reminders_text = "\n\nНапоминания:\n"
        for i, reminder in enumerate(reminders, 1):
            reminder_id, reminder_date, reminder_time = reminder
            reminders_text += f"{i}. {reminder_date} в {reminder_time}\n"
    else:
        reminders_text = "\n\nНапоминаний нет."
    
    keyboard = [
        [InlineKeyboardButton("Добавить напоминание", callback_data=f"event_{event_id}")],
        [InlineKeyboardButton("Удалить событие", callback_data=f"delete_event_{event_id}")],
        [InlineKeyboardButton("Назад к списку событий", callback_data="view_events")],
        [InlineKeyboardButton("Главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"Событие: {name}\nДата: {date}\nВремя: {time}{reminders_text}",
        reply_markup=reply_markup
    )
    
    return CHOOSING_ACTION

# Показать список событий для добавления напоминания
async def show_events_for_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    events = database.get_user_events(update.effective_user.id)
    
    if not events:
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text="У вас нет событий. Сначала добавьте событие.",
            reply_markup=reply_markup
        )
        return CHOOSING_ACTION
    
    keyboard = []
    for event in events:
        event_id, name, date, time = event
        keyboard.append([InlineKeyboardButton(f"{name} ({date} {time})", callback_data=f"event_{event_id}")])
    
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="Выберите событие для добавления напоминания:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_EVENT_FOR_REMINDER

# Показать список событий для удаления
async def show_events_for_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    events = database.get_user_events(update.effective_user.id)
    
    if not events:
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text="У вас нет событий для удаления.",
            reply_markup=reply_markup
        )
        return CHOOSING_ACTION
    
    keyboard = []
    for event in events:
        event_id, name, date, time = event
        keyboard.append([InlineKeyboardButton(f"{name} ({date} {time})", callback_data=f"delete_event_{event_id}")])
    
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="Выберите событие для удаления:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_EVENT_TO_DELETE

# Подтверждение удаления события
async def confirm_event_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    event_id = int(query.data.split("_")[2])
    context.user_data["event_id_to_delete"] = event_id
    
    # Получаем информацию о событии
    event = database.get_event(event_id)
    
    if not event:
        await query.edit_message_text(text="Событие не найдено.")
        return await show_main_menu(update, context)
    
    name, date, time = event
    
    # Получаем количество напоминаний для события
    reminder_count = database.get_reminder_count(event_id)
    
    reminder_text = f"\n\nВместе с событием будут удалены все связанные напоминания ({reminder_count})." if reminder_count > 0 else ""
    
    keyboard = [
        [InlineKeyboardButton("Да, удалить", callback_data=f"confirm_delete_event_{event_id}")],
        [InlineKeyboardButton("Нет, отменить", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"Вы уверены, что хотите удалить событие '{name}' ({date} {time})?{reminder_text}",
        reply_markup=reply_markup
    )
    
    return CONFIRMING_EVENT_DELETION

# Удаление события
async def delete_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    event_id = int(query.data.split("_")[3])
    
    # Удаляем событие и все связанные напоминания
    database.delete_event(event_id)
    
    keyboard = [[InlineKeyboardButton("Назад в главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="Событие и все связанные напоминания успешно удалены.",
        reply_markup=reply_markup
    )
    
    return CHOOSING_ACTION