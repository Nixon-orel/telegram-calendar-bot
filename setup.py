#!/usr/bin/env python3
"""
Скрипт для настройки бота-календаря
"""

import os
import sys
import subprocess
import shutil

def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 7):
        print("Ошибка: Требуется Python 3.7 или выше")
        sys.exit(1)
    print("✓ Версия Python соответствует требованиям")

def install_dependencies():
    """Установка зависимостей"""
    print("Установка зависимостей...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Зависимости успешно установлены")
    except subprocess.CalledProcessError:
        print("Ошибка: Не удалось установить зависимости")
        sys.exit(1)

def create_config():
    """Создание конфигурационного файла"""
    if os.path.exists("config.py"):
        print("Файл config.py уже существует")
        overwrite = input("Хотите перезаписать его? (y/n): ")
        if overwrite.lower() != 'y':
            print("✓ Используется существующий файл config.py")
            return
    
    if not os.path.exists("config.py.example"):
        print("Ошибка: Файл config.py.example не найден")
        sys.exit(1)
    
    shutil.copy("config.py.example", "config.py")
    print("✓ Файл config.py создан")
    
    # Запрос токена бота
    bot_token = input("Введите токен вашего Telegram бота (полученный от @BotFather): ")
    if bot_token:
        with open("config.py", "r") as f:
            config_content = f.read()
        
        config_content = config_content.replace("YOUR_TELEGRAM_BOT_TOKEN", bot_token)
        
        with open("config.py", "w") as f:
            f.write(config_content)
        
        print("✓ Токен бота сохранен в config.py")
    else:
        print("Токен бота не указан. Вам нужно будет вручную отредактировать файл config.py")

def main():
    """Основная функция"""
    print("Настройка бота-календаря")
    print("-----------------------")
    
    # Проверка версии Python
    check_python_version()
    
    # Установка зависимостей
    install_dependencies()
    
    # Создание конфигурационного файла
    create_config()
    
    print("-----------------------")
    print("Настройка завершена!")
    print("Теперь вы можете запустить бота с помощью команды:")
    print("python run.py")

if __name__ == "__main__":
    main()