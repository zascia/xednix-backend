import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
import os

app = Flask(__name__)

# Настройка логирования в файл
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/xednix_app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

app.config.from_object(Config)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
CORS(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

from routes import *
from models import *

if __name__ == '__main__':
    app.run(debug=True)