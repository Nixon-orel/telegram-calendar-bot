import logging
import asyncio
import datetime
import pytz
from telegram import Bot

# Импорт конфигурации
try:
    import config
except ImportError:
    print("Файл конфигурации не найден. Пожалуйста, создайте файл config.py на основе config.py.example")
    exit(1)

# Импорт модулей
import database
from handlers.common import get_user_timezone

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL),
    filename=config.SCHEDULER_LOG_FILE
)
logger = logging.getLogger(__name__)

async def send_reminder(bot, user_id, event_name, event_date, event_time):
    """Отправляет напоминание пользователю"""
    try:
        message = f"🔔 НАПОМИНАНИЕ 🔔\n\nСобытие: {event_name}\nДата: {event_date}\nВремя: {event_time}"
        await bot.send_message(chat_id=user_id, text=message)
        logger.info(f"Напоминание отправлено пользователю {user_id} о событии '{event_name}'")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания: {e}")

async def check_reminders():
    """Проверяет напоминания и отправляет их, если время наступило"""
    bot = Bot(token=config.BOT_TOKEN)
    
    while True:
        try:
            # Подключение к базе данных
            conn = database.sqlite3.connect(config.DB_NAME)
            cursor = conn.cursor()
            
            # Получаем всех пользователей с их часовыми поясами
            cursor.execute("SELECT DISTINCT user_id FROM user_settings")
            users = cursor.fetchall()
            
            # Если нет пользователей в таблице user_settings, проверяем всех пользователей из таблицы events
            if not users:
                cursor.execute("SELECT DISTINCT user_id FROM events")
                users = cursor.fetchall()
            
            # Проверяем напоминания для каждого пользователя в его часовом поясе
            for user in users:
                user_id = user[0]
                timezone_str = get_user_timezone(user_id)
                
                try:
                    # Получаем текущее время в часовом поясе пользователя
                    timezone = pytz.timezone(timezone_str)
                    now = datetime.datetime.now(timezone)
                    current_date = now.strftime("%d.%m.%Y")
                    current_time = now.strftime("%H:%M")
                    
                    # Получаем напоминания для этого пользователя, время которых наступило
                    cursor.execute("""
                        SELECT r.id, e.user_id, e.name, e.event_date, e.event_time
                        FROM reminders r
                        JOIN events e ON r.event_id = e.id
                        WHERE e.user_id = ? AND r.reminder_date = ? AND r.reminder_time = ?
                    """, (user_id, current_date, current_time))
                    
                    reminders = cursor.fetchall()
                    
                    # Отправляем напоминания
                    for reminder in reminders:
                        reminder_id, user_id, event_name, event_date, event_time = reminder
                        await send_reminder(bot, user_id, event_name, event_date, event_time)
                        
                        # Удаляем напоминание после отправки
                        database.delete_reminder(reminder_id)
                
                except Exception as e:
                    logger.error(f"Ошибка при проверке напоминаний для пользователя {user_id}: {e}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка при проверке напоминаний: {e}")
        
        # Ждем до следующей проверки
        await asyncio.sleep(config.CHECK_INTERVAL)

async def main():
    """Основная функция"""
    # Инициализация базы данных
    database.init_db()
    
    logger.info("Планировщик напоминаний запущен")
    await check_reminders()

if __name__ == "__main__":
    try:
        # Запускаем планировщик напоминаний
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Планировщик напоминаний остановлен")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")