import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# Импорт конфигурации
try:
    import config
except ImportError:
    print("Файл конфигурации не найден. Пожалуйста, создайте файл config.py на основе config.py.example")
    exit(1)

# Импорт модулей
import database
from handlers.common import (
    CHOOSING_ACTION, ADDING_EVENT_NAME, ADDING_EVENT_DATE, ADDING_EVENT_TIME,
    ADDING_REMINDER, CHOOSING_EVENT_FOR_REMINDER, ADDING_REMINDER_DATE,
    ADDING_REMINDER_TIME, CHOOSING_EVENT_TO_VIEW, CHOOSING_TIMEZONE,
    CHOOSING_EVENT_TO_DELETE, CONFIRMING_EVENT_DELETION,
    CHOOSING_REMINDER_TO_DELETE, CONFIRMING_REMINDER_DELETION,
    show_main_menu, handle_menu_choice, cancel
)
from handlers.event_handlers import (
    add_event_name, add_event_date, add_event_time,
    show_events, view_event_details, show_events_for_reminder,
    show_events_for_deletion, confirm_event_deletion, delete_event
)
from handlers.reminder_handlers import (
    choose_event_for_reminder, add_reminder_date, add_reminder_time,
    show_events_for_reminder_deletion, show_reminders_for_deletion,
    confirm_reminder_deletion, delete_reminder
)
from handlers.settings_handlers import (
    show_timezone_selection, set_timezone_handler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL),
    filename=config.LOG_FILE
)
logger = logging.getLogger(__name__)

# Команда /start
async def start(update: ContextTypes.DEFAULT_TYPE, context) -> int:
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот-календарь. Я помогу тебе управлять твоими событиями и напоминаниями."
    )
    return await show_main_menu(update, context)

def main():
    # Инициализация базы данных
    database.init_db()
    
    # Создание приложения
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Создание обработчика разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [
                CallbackQueryHandler(handle_menu_choice, pattern="^(add_event|add_reminder|view_events|delete_event|delete_reminder|current_time|set_timezone)$"),
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
                CallbackQueryHandler(show_reminders_for_deletion, pattern="^delete_reminder_event_[0-9]+$"),
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
                CallbackQueryHandler(confirm_event_deletion, pattern="^delete_event_[0-9]+$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_menu$"),
            ],
            CHOOSING_TIMEZONE: [
                CallbackQueryHandler(set_timezone_handler, pattern="^tz_"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_menu$"),
            ],
            CHOOSING_EVENT_TO_DELETE: [
                CallbackQueryHandler(confirm_event_deletion, pattern="^delete_event_[0-9]+$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_menu$"),
            ],
            CONFIRMING_EVENT_DELETION: [
                CallbackQueryHandler(delete_event, pattern="^confirm_delete_event_[0-9]+$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_menu$"),
            ],
            CHOOSING_REMINDER_TO_DELETE: [
                CallbackQueryHandler(confirm_reminder_deletion, pattern="^delete_reminder_[0-9]+$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_menu$"),
            ],
            CONFIRMING_REMINDER_DELETION: [
                CallbackQueryHandler(delete_reminder, pattern="^confirm_delete_reminder_[0-9]+$"),
                CallbackQueryHandler(show_main_menu, pattern="^back_to_menu$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling()
    
if __name__ == "__main__":
    main()