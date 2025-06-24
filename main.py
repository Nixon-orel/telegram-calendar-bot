import logging
import datetime
import sqlite3
import os
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

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
) = range(10)

# Функция для инициализации базы данных
def init_db():
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    # Создаем таблицу для событий
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        event_date TEXT NOT NULL,
        event_time TEXT NOT NULL
    )
    ''')
    
    # Создаем таблицу для напоминаний
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY,
        event_id INTEGER NOT NULL,
        reminder_date TEXT NOT NULL,
        reminder_time TEXT NOT NULL,
        FOREIGN KEY (event_id) REFERENCES events (id)
    )
    ''')
    
    # Создаем таблицу для настроек пользователей
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        timezone TEXT NOT NULL DEFAULT '{config.DEFAULT_TIMEZONE}'
    )
    ''')
    
    conn.commit()
    conn.close()

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

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот-календарь. Я помогу тебе управлять твоими событиями и напоминаниями."
    )
    return await show_main_menu(update, context)

# Показать главное меню
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("Добавить событие", callback_data="add_event")],
        [InlineKeyboardButton("Добавить напоминание", callback_data="add_reminder")],
        [InlineKeyboardButton("Просмотреть события", callback_data="view_events")],
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

# Обработка выбора действия
async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    
    if choice == "add_event":
        await query.edit_message_text(text="Введите название события:")
        return ADDING_EVENT_NAME
    elif choice == "add_reminder":
        return await show_events_for_reminder(update, context)
    elif choice == "view_events":
        return await show_events(update, context)
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
        return await show_timezone_selection(update, context)

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
        conn = sqlite3.connect(config.DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO events (user_id, name, event_date, event_time) VALUES (?, ?, ?, ?)",
            (update.effective_user.id, context.user_data["event_name"], context.user_data["event_date"], context.user_data["event_time"])
        )
        
        event_id = cursor.lastrowid
        context.user_data["event_id"] = event_id
        
        conn.commit()
        conn.close()
        
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

# Показать список событий для добавления напоминания
async def show_events_for_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, name, event_date, event_time FROM events WHERE user_id = ?",
        (update.effective_user.id,)
    )
    
    events = cursor.fetchall()
    conn.close()
    
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

# Выбор события для напоминания
async def choose_event_for_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    event_id = int(query.data.split("_")[1])
    context.user_data["event_id"] = event_id
    
    # Получаем информацию о событии
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT name, event_date, event_time FROM events WHERE id = ?",
        (event_id,)
    )
    
    event = cursor.fetchone()
    conn.close()
    
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
        conn = sqlite3.connect(config.DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO reminders (event_id, reminder_date, reminder_time) VALUES (?, ?, ?)",
            (context.user_data["event_id"], context.user_data["reminder_date"], context.user_data["reminder_time"])
        )
        
        conn.commit()
        conn.close()
        
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

# Показать список событий
async def show_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, name, event_date, event_time FROM events WHERE user_id = ? ORDER BY event_date, event_time",
        (update.effective_user.id,)
    )
    
    events = cursor.fetchall()
    conn.close()
    
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
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT name, event_date, event_time FROM events WHERE id = ?",
        (event_id,)
    )
    
    event = cursor.fetchone()
    
    if not event:
        await query.edit_message_text(text="Событие не найдено.")
        return await show_main_menu(update, context)
    
    name, date, time = event
    
    # Получаем напоминания для события
    cursor.execute(
        "SELECT reminder_date, reminder_time FROM reminders WHERE event_id = ? ORDER BY reminder_date, reminder_time",
        (event_id,)
    )
    
    reminders = cursor.fetchall()
    conn.close()
    
    reminders_text = ""
    if reminders:
        reminders_text = "\n\nНапоминания:\n"
        for i, reminder in enumerate(reminders, 1):
            reminder_date, reminder_time = reminder
            reminders_text += f"{i}. {reminder_date} в {reminder_time}\n"
    else:
        reminders_text = "\n\nНапоминаний нет."
    
    keyboard = [
        [InlineKeyboardButton("Добавить напоминание", callback_data=f"event_{event_id}")],
        [InlineKeyboardButton("Назад к списку событий", callback_data="view_events")],
        [InlineKeyboardButton("Главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"Событие: {name}\nДата: {date}\nВремя: {time}{reminders_text}",
        reply_markup=reply_markup
    )
    
    return CHOOSING_ACTION

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
async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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

# Обработка команды /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.")
    return await show_main_menu(update, context)

def main():
    # Инициализация базы данных
    init_db()
    
    # Создание приложения
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Создание обработчика разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [
                CallbackQueryHandler(handle_menu_choice, pattern="^(add_event|add_reminder|view_events|current_time|set_timezone)$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_menu$"),
            ],
            ADDING_EVENT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_event_name)
            ],
            ADDING_EVENT_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_event_date)
            ],
            ADDING_EVENT_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_event_time)
            ],
            ADDING_REMINDER: [
                CallbackQueryHandler(choose_event_for_reminder, pattern="^add_reminder_now$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_menu$"),
            ],
            CHOOSING_EVENT_FOR_REMINDER: [
                CallbackQueryHandler(choose_event_for_reminder, pattern="^event_[0-9]+$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_menu$"),
            ],
            ADDING_REMINDER_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_date)
            ],
            ADDING_REMINDER_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_time)
            ],
            CHOOSING_EVENT_TO_VIEW: [
                CallbackQueryHandler(view_event_details, pattern="^view_event_[0-9]+$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_menu$"),
            ],
            CHOOSING_TIMEZONE: [
                CallbackQueryHandler(set_timezone, pattern="^tz_"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_menu$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()