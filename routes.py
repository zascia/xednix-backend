import requests
import os
from dotenv import load_dotenv
from flask import jsonify, request
from app import app, db, bcrypt
from models import User
import logging
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required, get_jwt_identity

logger = logging.getLogger(__name__)

load_dotenv()
JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")

@app.route('/')
def hello_world():
    return jsonify({"message": "Hello, Xednix!"})


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # Проверка на наличие всех полей
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'All fields are required'}), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Проверка, существует ли пользователь
    if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
        return jsonify({'error': 'Username or email already exists'}), 409

    # Хеширование пароля
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    # Создание нового пользователя
    new_user = User(username=username, email=email, password_hash=hashed_password)

    # Добавление пользователя в сессию и сохранение в базу данных
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully!'}), 201


# Маршрут для авторизации
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('username_or_email') or not data.get('password'):
        return jsonify({'error': 'All fields are required'}), 400

    username_or_email = data.get('username_or_email')
    password = data.get('password')

    # 1. Поиск пользователя по имени или email
    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    # 2. Проверка существования пользователя и пароля
    if user and bcrypt.check_password_hash(user.password_hash, password):

        # 3. Генерация JWT-токена
        # Мы кодируем ID пользователя в токен !!! user.id преобразуется В СТРОКУ!
        access_token = create_access_token(identity=str(user.id))

        logger.info(f"User {user.username} successfully logged in.")

        # 4. Возвращаем токен клиенту
        return jsonify(
            message='Login successful',
            access_token=access_token,
            username=user.username
        ), 200

    # Если пользователь не найден или пароль неверен
    return jsonify({'error': 'Invalid credentials'}), 401


# Защищенный маршрут (примитивная админка/дашборд)
@app.route('/dashboard', methods=['GET'])
@jwt_required() # <--- ЭТО ЗАЩИЩАЕТ МАРШРУТ
def dashboard():
    # Получаем ID пользователя из токена (помнить, что current_user_id это строка)
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    if user:
        return jsonify({
            "message": f"Welcome to the Dashboard, {user.username}!",
            "user_id": current_user_id,
            "access_level": "Standard" # Здесь может быть проверка ролей
        }), 200

    return jsonify({"error": "User not found"}), 404


# (Маршрут получения ресурсов, доступных для поиска вакансий)
@app.route('/api/resources', methods=['GET'])
@jwt_required()
def get_job_resources():
    active_resources = JobResource.query.filter_by(is_active=True).all()
    resources_list = [resource.to_dict() for resource in active_resources]
    return jsonify(resources_list), 200

# Маршрут добавления ресурсов для администратора/тестирования
@app.route('/api/resource/add', methods=['POST'])
@jwt_required() # Защищен токеном
def add_job_resource():
    # ... (логика получения данных, добавления в БД и обработки ошибок)
    # Используйте Postman для добавления Jooble, LinkedIn, Indeed.
    # Пример:
    # new_resource = JobResource(name='Jooble', base_url='https://jooble.org/api/', api_key_required=True)
    # db.session.add(new_resource)
    # db.session.commit()
    pass

# обрабатывает поисковый запрос и список выбранных ресурсов, выполняя вызов к Jooble API
@app.route('/api/search', methods=['POST'])
@jwt_required()
def search_jobs():
    data = request.get_json()
    term = data.get('searchTerm')
    resource_ids = data.get('resourceIds')

    # ... (проверка входных данных)

    results = []
    resources_to_search = JobResource.query.filter(JobResource.id.in_(resource_ids)).all()

    for resource in resources_to_search:
        if resource.name == 'Jooble':
            if not JOOBLE_API_KEY:
                logger.error("JOOBLE_API_KEY is missing from environment variables.")
                return jsonify({'error': 'Server configuration error: API key missing'}), 500

            # ... (используйте ключ в запросе к Jooble) ...
            jooble_url = f"{resource.base_url}{JOOBLE_API_KEY}"

            # ... (логика формирования JSON-запроса для Jooble)
            # Убедитесь, что ваш Jooble-запрос включает нужные локации (Europe, Ukraine, USA)

            # ... (выполнение requests.post к Jooble)

            # ... (обработка и форматирование результатов в единый формат 'id', 'title', 'company', 'link', 'source' и т.д.)

            # ВАЖНО: Здесь будет место для внедрения ИИ-матчинга
            #
            # if USE_AI_MATCHING:
            #     matched_jobs = ai_matcher(raw_jobs, applicant_skills)
            #     results.extend(matched_jobs)
            # else:
            #     results.extend(formatted_jobs)

    return jsonify(results), 200

