import sqlite3
import logging

# Импорт конфигурации
try:
    import config
except ImportError:
    print("Файл конфигурации не найден. Пожалуйста, создайте файл config.py на основе config.py.example")
    exit(1)

logger = logging.getLogger(__name__)

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
    logger.info("База данных инициализирована")

# Функция для добавления события
def add_event(user_id, name, event_date, event_time):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO events (user_id, name, event_date, event_time) VALUES (?, ?, ?, ?)",
        (user_id, name, event_date, event_time)
    )
    
    event_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    logger.info(f"Добавлено событие: {name} для пользователя {user_id}")
    return event_id

# Функция для добавления напоминания
def add_reminder(event_id, reminder_date, reminder_time):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO reminders (event_id, reminder_date, reminder_time) VALUES (?, ?, ?)",
        (event_id, reminder_date, reminder_time)
    )
    
    reminder_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    logger.info(f"Добавлено напоминание для события {event_id}")
    return reminder_id

# Функция для получения событий пользователя
def get_user_events(user_id):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, name, event_date, event_time FROM events WHERE user_id = ? ORDER BY event_date, event_time",
        (user_id,)
    )
    
    events = cursor.fetchall()
    conn.close()
    
    return events

# Функция для получения событий пользователя с напоминаниями
def get_user_events_with_reminders(user_id):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT e.id, e.name, e.event_date, e.event_time 
        FROM events e
        JOIN reminders r ON e.id = r.event_id
        WHERE e.user_id = ?
        ORDER BY e.event_date, e.event_time
    """, (user_id,))
    
    events = cursor.fetchall()
    conn.close()
    
    return events

# Функция для получения информации о событии
def get_event(event_id):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT name, event_date, event_time FROM events WHERE id = ?",
        (event_id,)
    )
    
    event = cursor.fetchone()
    conn.close()
    
    return event

# Функция для получения напоминаний для события
def get_event_reminders(event_id):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, reminder_date, reminder_time FROM reminders WHERE event_id = ? ORDER BY reminder_date, reminder_time",
        (event_id,)
    )
    
    reminders = cursor.fetchall()
    conn.close()
    
    return reminders

# Функция для получения информации о напоминании
def get_reminder(reminder_id):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT reminder_date, reminder_time FROM reminders WHERE id = ?",
        (reminder_id,)
    )
    
    reminder = cursor.fetchone()
    conn.close()
    
    return reminder

# Функция для удаления события и всех связанных напоминаний
def delete_event(event_id):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    # Сначала удаляем напоминания
    cursor.execute(
        "DELETE FROM reminders WHERE event_id = ?",
        (event_id,)
    )
    
    # Затем удаляем событие
    cursor.execute(
        "DELETE FROM events WHERE id = ?",
        (event_id,)
    )
    
    conn.commit()
    conn.close()
    
    logger.info(f"Удалено событие {event_id} и все связанные напоминания")

# Функция для удаления напоминания
def delete_reminder(reminder_id):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "DELETE FROM reminders WHERE id = ?",
        (reminder_id,)
    )
    
    conn.commit()
    conn.close()
    
    logger.info(f"Удалено напоминание {reminder_id}")

# Функция для получения количества напоминаний для события
def get_reminder_count(event_id):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT COUNT(*) FROM reminders WHERE event_id = ?",
        (event_id,)
    )
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count