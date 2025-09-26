import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Настройки для JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'your-very-secret-jwt-key' # <--- ДОБАВИТЬ
    # Установите, что токен действует 1 день
    JWT_ACCESS_TOKEN_EXPIRES = 86400