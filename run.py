#!/usr/bin/env python3
"""
Скрипт для одновременного запуска бота и планировщика напоминаний
"""

import subprocess
import sys
import os
import time
import signal
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='run.log'
)
logger = logging.getLogger(__name__)

# Проверка наличия конфигурационного файла
if not os.path.exists('config.py'):
    print("Файл конфигурации не найден. Пожалуйста, создайте файл config.py на основе config.py.example")
    sys.exit(1)

# Проверка наличия необходимых файлов
required_files = ['main.py', 'reminder_scheduler.py']
for file in required_files:
    if not os.path.exists(file):
        print(f"Файл {file} не найден. Убедитесь, что все необходимые файлы находятся в текущей директории.")
        sys.exit(1)

# Список процессов
processes = []

def signal_handler(sig, frame):
    """Обработчик сигналов для корректного завершения процессов"""
    print("\nЗавершение работы...")
    for process in processes:
        if process.poll() is None:  # Если процесс еще работает
            process.terminate()
    sys.exit(0)

# Регистрация обработчика сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Основная функция"""
    try:
        # Запуск бота
        print("Запуск бота...")
        bot_process = subprocess.Popen([sys.executable, 'main.py'])
        processes.append(bot_process)
        logger.info("Бот запущен")
        
        # Запуск планировщика напоминаний
        print("Запуск планировщика напоминаний...")
        scheduler_process = subprocess.Popen([sys.executable, 'reminder_scheduler.py'])
        processes.append(scheduler_process)
        logger.info("Планировщик напоминаний запущен")
        
        print("Бот и планировщик напоминаний запущены. Нажмите Ctrl+C для завершения.")
        
        # Ожидание завершения процессов
        while True:
            # Проверка статуса процессов
            if bot_process.poll() is not None:
                print("Бот неожиданно завершил работу. Перезапуск...")
                bot_process = subprocess.Popen([sys.executable, 'main.py'])
                processes[0] = bot_process
                logger.warning("Бот перезапущен после неожиданного завершения")
            
            if scheduler_process.poll() is not None:
                print("Планировщик напоминаний неожиданно завершил работу. Перезапуск...")
                scheduler_process = subprocess.Popen([sys.executable, 'reminder_scheduler.py'])
                processes[1] = scheduler_process
                logger.warning("Планировщик напоминаний перезапущен после неожиданного завершения")
            
            time.sleep(5)
    
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
        for process in processes:
            if process.poll() is None:  # Если процесс еще работает
                process.terminate()
        logger.info("Бот и планировщик напоминаний остановлены")
    
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        logger.error(f"Неожиданная ошибка: {e}")
        for process in processes:
            if process.poll() is None:  # Если процесс еще работает
                process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()