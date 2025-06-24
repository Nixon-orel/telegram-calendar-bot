import logging
import datetime
import sqlite3
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Импорт конфигурации
try:
    import config
except ImportError:
    print("Файл конфигурации не найден. Пожалуйста, создайте файл config.py на основе config.py.example")
    exit(1)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL),
    filename=config.LOG_FILE
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(
    CHOOSING_ACTION,
    ADDING_EVENT_NAME,
    ADDING_EVENT_DATE,
    ADDING_EVENT_TIME,
    ADDING_REMINDER,
    CHOOSING_EVENT_FOR_REMINDER,
    ADDING_REMINDER_DATE,
    ADDING_REMINDER_TIME,
    CHOOSING_EVENT_TO_VIEW,
    CHOOSING_TIMEZONE,
    CHOOSING_EVENT_TO_DELETE,
    CONFIRMING_EVENT_DELETION,
    CHOOSING_REMINDER_TO_DELETE,
    CONFIRMING_REMINDER_DELETION,
) = range(14)

# Функция для получения часового пояса пользователя
def get_user_timezone(user_id):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT timezone FROM user_settings WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        timezone = result[0]
    else:
        # Если пользователя нет в базе, добавляем его с часовым поясом по умолчанию
        timezone = config.DEFAULT_TIMEZONE
        cursor.execute("INSERT INTO user_settings (user_id, timezone) VALUES (?, ?)",
                      (user_id, timezone))
        conn.commit()
    
    conn.close()
    return timezone

# Функция для установки часового пояса пользователя
def set_user_timezone(user_id, timezone):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("INSERT OR REPLACE INTO user_settings (user_id, timezone) VALUES (?, ?)",
                  (user_id, timezone))
    
    conn.commit()
    conn.close()

# Функция для получения текущего времени в часовом поясе пользователя
def get_user_current_time(user_id):
    timezone_str = get_user_timezone(user_id)
    timezone = pytz.timezone(timezone_str)
    return datetime.datetime.now(timezone)

# Показать главное меню
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("Добавить событие", callback_data="add_event")],
        [InlineKeyboardButton("Добавить напоминание", callback_data="add_reminder")],
        [InlineKeyboardButton("Просмотреть события", callback_data="view_events")],
        [InlineKeyboardButton("Удалить событие", callback_data="delete_event")],
        [InlineKeyboardButton("Удалить напоминание", callback_data="delete_reminder")],
        [InlineKeyboardButton("Текущее время и дата", callback_data="current_time")],
        [InlineKeyboardButton("Настройка часового пояса", callback_data="set_timezone")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text="Выберите действие:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text="Выберите действие:",
            reply_markup=reply_markup
        )
    
    return CHOOSING_ACTION

# Обработка команды /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.")
    return await show_main_menu(update, context)

# Обработка выбора действия
async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    
    if choice == "add_event":
        await query.edit_message_text(text="Введите название события:")
        return ADDING_EVENT_NAME
    elif choice == "add_reminder":
        from .event_handlers import show_events_for_reminder
        return await show_events_for_reminder(update, context)
    elif choice == "view_events":
        from .event_handlers import show_events
        return await show_events(update, context)
    elif choice == "delete_event":
        from .event_handlers import show_events_for_deletion
        return await show_events_for_deletion(update, context)
    elif choice == "delete_reminder":
        from .reminder_handlers import show_events_for_reminder_deletion
        return await show_events_for_reminder_deletion(update, context)
    elif choice == "current_time":
        user_id = update.effective_user.id
        now = get_user_current_time(user_id)
        timezone_str = get_user_timezone(user_id)
        
        formatted_date = now.strftime("%d.%m.%Y")
        formatted_time = now.strftime("%H:%M:%S")
        
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"Текущая дата: {formatted_date}\nТекущее время: {formatted_time}\nЧасовой пояс: {timezone_str}",
            reply_markup=reply_markup
        )
        return CHOOSING_ACTION
    elif choice == "set_timezone":
        from .settings_handlers import show_timezone_selection
        return await show_timezone_selection(update, context)