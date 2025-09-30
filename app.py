import logging
import sys
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
import os
from flasgger import Swagger
import logging.handlers

# --- Инициализация Flask и Swagger (должно быть первым) ---
app = Flask(__name__)
swagger = Swagger(app)

# -------------------------------------------------------------
# 1. КОНФИГУРАЦИЯ ЛОГИРОВАНИЯ (Исправленная версия с UTF-8)
# -------------------------------------------------------------

# Получаем корневой логгер Python
root = logging.getLogger()
root.handlers = [] # Очищаем все, что было настроено ранее
root.setLevel(logging.INFO) # Устанавливаем минимальный уровень

if not app.debug:
    # 1.1. Настройка для файлового логирования (для Promtail/Loki)
    if not os.path.exists('logs'):
        os.mkdir('logs')
    # Добавляем encoding='utf8'
    # Изменение размера лога до 10 МБ в maxBytes (10 * 1024 * 1024 байт)
    file_handler = RotatingFileHandler('logs/xednix_app.log', maxBytes=102400, backupCount=10, encoding='utf8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    root.addHandler(file_handler)

    # 1.2. ДОБАВЛЯЕМ StreamHandler для консоли
    # Нам нужно обеспечить UTF-8 для консоли, используя sys.stdout.reconfigure()
    # (работает только в Python 3.7+), или установить кодировку в самом обработчике.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    console_handler.setLevel(logging.INFO)
    root.addHandler(console_handler)

# -------------------------------------------------------------
# 2. Инициализация расширений Flask
# -------------------------------------------------------------
app.config.from_object(Config)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
CORS(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# -------------------------------------------------------------
# 3. Импорт маршрутов и моделей (должен быть последним)
# -------------------------------------------------------------
from routes import *
from models import *

if __name__ == '__main__':
    # Если запускаем через 'python app.py', включаем debug,
    # иначе используем настройки выше для 'flask run'
    app.run(debug=True)
