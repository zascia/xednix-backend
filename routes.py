import requests
import os
from dotenv import load_dotenv
from flask import jsonify, request
from app import app, db, bcrypt
from models import User, JobResource, ApplicantProfile, Skill, RoleFocus
from ai_matcher import ai_match_jobs
import json
import logging
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

load_dotenv()
JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")

@app.route('/')
def hello_world():
    """
    Проверка работоспособности API.
    ---
    tags:
      - Общее
    responses:
      200:
        description: Приветственное сообщение.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Hello, Xednix!
    """
    return jsonify({"message": "Hello, Xednix!"})


@app.route('/register', methods=['POST'])
def register():
    """
    Регистрация нового пользователя.
    ---
    tags:
      - Аутентификация
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              example: testuser
            email:
              type: string
              example: user@example.com
            password:
              type: string
              example: strongpassword123
    responses:
      201:
        description: Пользователь успешно зарегистрирован.
      400:
        description: Обязательные поля не заполнены.
      409:
        description: Пользователь с таким email или логином уже существует.
    """
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
    """
    Авторизация пользователя.
    ---
    tags:
      - Аутентификация
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            username_or_email:
              type: string
              description: Логин или email пользователя.
              example: testuser
            password:
              type: string
              example: strongpassword123
    responses:
      200:
        description: Успешная авторизация, возвращает JWT токен.
        schema:
          type: object
          properties:
            access_token:
              type: string
            message:
              type: string
            username:
              type: string
      401:
        description: Неверные учетные данные.
    """
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
    """
    Получение приветственного сообщения на Дашборде (защищен).
    ---
    tags:
      - Пользователь
    security:
      - Bearer: []
    responses:
      200:
        description: Приветственное сообщение для авторизованного пользователя.
      401:
        description: Отсутствует или недействительный токен.
    """
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
    """
    Получение списка активных ресурсов (Jooble, Indeed и т.д.).
    ---
    tags:
      - Ресурсы
    security:
      - Bearer: []
    responses:
      200:
        description: Список доступных ресурсов.
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              is_active:
                type: boolean
      401:
        description: Отсутствует или недействительный токен.
    """
    active_resources = JobResource.query.filter_by(is_active=True).all()
    resources_list = [resource.to_dict() for resource in active_resources]
    return jsonify(resources_list), 200

# Маршрут добавления ресурсов для администратора/тестирования
@app.route('/api/resource/add', methods=['POST'])
@jwt_required() # Защищен токеном
def add_job_resource():
    """
    Добавление нового ресурса (Jooble, Indeed) в базу данных.
    ---
    tags:
      - Ресурсы
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: Jooble
            base_url:
              type: string
              example: https://jooble.org/api/
            is_active:
              type: boolean
              example: true
    responses:
      201:
        description: Ресурс успешно добавлен.
      409:
        description: Ресурс с таким именем уже существует.
    """
    data = request.get_json()
    if not data or not data.get('name') or not data.get('base_url'):
        return jsonify({'error': 'Name and URL are required'}), 400

    if JobResource.query.filter_by(name=data['name']).first():
        return jsonify({'error': f"Resource {data['name']} already exists"}), 409

    new_resource = JobResource(
        name=data['name'],
        base_url=data['base_url'],
        is_active=data.get('is_active', True),
        api_key_required=data.get('api_key_required', False)
    )

    try:
        db.session.add(new_resource)
        db.session.commit()
        return jsonify({'message': f'Resource {new_resource.name} added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding resource: {e}")
        return jsonify({'error': 'Database error occurred'}), 500


# обрабатывает поисковый запрос и список выбранных ресурсов, выполняя вызов к Jooble API
@app.route('/api/search', methods=['POST'])
@jwt_required()
def search_jobs():
    """
    Поиск вакансий по ключевым словам, локации и уровню.
    ---
    tags:
      - Поиск
    security:
      - Bearer: []
    parameters:
      - in: body
        name: search_params
        required: true
        schema:
          type: object
          properties:
            searchTerm:
              type: string
              description: Ключевые слова для поиска (например, Frontend developer).
              example: Python developer
            resourceIds:
              type: array
              items:
                type: integer
              description: ID выбранных ресурсов для поиска (например, [1]).
            location:
              type: string
              description: Локация для поиска (например, Berlin, Europe).
              example: Berlin
            level:
              type: string
              description: Уровень соискателя (например, средний).
              example: средний
    responses:
      200:
        description: Успешный список найденных вакансий.
        schema:
          type: array
          items:
            type: object
            properties:
              title:
                type: string
              company:
                type: string
      400:
        description: Отсутствуют обязательные параметры поиска.
    """
    data = request.get_json()
    term = data.get('searchTerm')
    resource_ids = data.get('resourceIds')
    location = data.get('location')
    level = data.get('level')

    # ... (проверка входных данных)
    if not term or not resource_ids:
        return jsonify({'error': 'Search term and at least one resource must be selected'}), 400


    resources_to_search = JobResource.query.filter(JobResource.id.in_(resource_ids)).all()

    # --- 1. ПОЛУЧЕНИЕ ДАННЫХ ПРОФИЛЯ ДЛЯ ИИ ---
    user_id = get_jwt_identity()
    profile = ApplicantProfile.query.filter_by(user_id=user_id).first()
    role_focus = RoleFocus.query.filter_by(profile_id=profile.id).order_by(RoleFocus.date.desc()).first()

    # Полный набор навыков (100% дата сет)
    full_user_skills = [skill.name for skill in profile.skills] if profile else []

    # Исключаемые навыки
    excluded_skills = []
    if role_focus and role_focus.focused_skills_data:
        focus_data = json.loads(role_focus.focused_skills_data)
        excluded_skills = focus_data.get('excluded_skills', [])

    raw_jobs = [] # Массив для сырых вакансий, полученных от Jooble

    for resource in resources_to_search:
        if resource.name == 'Jooble':
            if not JOOBLE_API_KEY:
                logger.error("JOOBLE_API_KEY is missing from environment variables.")
                return jsonify({'error': 'Server configuration error: API key missing'}), 500


            try:
                # У Jooble нет прямого поля для level (начальный/средний), поэтому мы добавим его к ключевым словам (keywords)
                full_keywords = f"{term} {level}"

                # 1. Формирование запроса Jooble
                json_data = {
                    "keywords": full_keywords,
                    "location": location,
                    "page": 1
                }

                jooble_url = f"{resource.base_url}{JOOBLE_API_KEY}"

                # 2. Выполнение запроса
                response = requests.post(jooble_url, json=json_data)
                response.raise_for_status() # Обработка ошибок HTTP
                jooble_data = response.json()

                # 3. Обработка и форматирование результатов
                if 'jobs' in jooble_data:
                    for job in jooble_data['jobs']:
                        # Вместо добавления в results, добавляем в raw_jobs для ИИ
                        raw_jobs.append({
                            'id': f"jooble_{job.get('id')}",
                            'title': job.get('title'),
                            'company': job.get('company'),
                            'location': job.get('location'),
                            'salary': job.get('salary') or 'N/A',
                            'source': resource.name,
                            'link': job.get('link'),
                            'description': job.get('snippet', '') # Описание для анализа!
                        })

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching data from Jooble: {e}")
                results.append({'error': f'Jooble search failed: {e}'})


            # --- 2. ПРИМЕНЕНИЕ ИИ-МАТЧИНГА ---
            if raw_jobs and full_user_skills:
                final_results = ai_match_jobs(raw_jobs, full_user_skills, excluded_skills)
                return jsonify(final_results), 200

            # Если профиль не настроен или нет вакансий
            return jsonify({'message': 'No relevant jobs found or profile incomplete'}), 200


# Маршрут для получения или создания профиля соискателя
@app.route('/api/profile', methods=['GET', 'POST'])
@jwt_required()
def handle_applicant_profile():
    """
    Получение или обновление основного профиля соискателя (текст резюме, навыки).
    ---
    tags:
      - Профиль
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            identified_role:
              type: string
              example: Frontend Developer
            resume_text:
              type: string
              description: Полный текст загруженного резюме.
            skills:
              type: array
              items:
                type: string
              description: Список ключевых навыков соискателя.
    responses:
      200:
        description: Данные профиля успешно получены или обновлены.
      404:
        description: Профиль соискателя не найден (для GET).
    """
    user_id = get_jwt_identity()

    if request.method == 'GET':
        # Получение данных профиля
        profile = ApplicantProfile.query.filter_by(user_id=user_id).first()

        if not profile:
            return jsonify({'message': 'Profile not created yet'}), 404

        # 1. Получаем последнюю сохраненную цель (RoleFocus)
        role_focus = RoleFocus.query.filter_by(profile_id=profile.id).order_by(RoleFocus.date.desc()).first()

        # 2. Формируем ответ
        response_data = {
            'profile_id': profile.id,
            'resume_status': 'Loaded' if profile.resume_text else 'Empty',
            'skills': [skill.name for skill in profile.skills], # Полный набор навыков
            'target_role': None,
            'target_level': None,
            'location': None
        }

        if role_focus:
            # Если найдена запись RoleFocus (т.е. Слепой поиск был настроен)
            response_data['target_role'] = role_focus.target_role
            response_data['target_level'] = role_focus.target_level

            # Локация хранится в JSON-поле focused_skills_data
            import json
            focus_data = json.loads(role_focus.focused_skills_data) if role_focus.focused_skills_data else {}
            response_data['location'] = focus_data.get('location')

        return jsonify(response_data), 200

    elif request.method == 'POST':
        data = request.get_json()

        # 1. Поиск или создание профиля
        profile = ApplicantProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = ApplicantProfile(user_id=user_id)
            db.session.add(profile)

        # 2. Обновление роли и резюме
        if data.get('identified_role'):
            profile.identified_role = data['identified_role']

        if data.get('resume_text'):
            profile.resume_text = data['resume_text']

        # 3. Обновление навыков (для ручного ввода или анализа)
        if data.get('skills'):
            # Очищаем старые навыки и добавляем новые
            profile.skills.clear()
            for skill_name in data['skills']:
                # Ищем или создаем новый навык в таблице Skill
                skill = Skill.query.filter_by(name=skill_name).first()
                if not skill:
                    skill = Skill(name=skill_name)
                    db.session.add(skill)
                profile.skills.append(skill)

        try:
            db.session.commit()
            return jsonify({'message': 'Profile updated successfully'}), 200
        except IntegrityError:
            db.session.rollback()
            return jsonify({'error': 'Error saving profile data'}), 500

# Маршрут для сохранения профиля Слепого поиска
@app.route('/api/profile/blind', methods=['POST'])
@jwt_required()
def save_blind_profile():
    """
    Сохранение данных профиля для режима 'Слепой поиск' (RoleFocus).
    ---
    tags:
      - Профиль
    security:
      - Bearer: []
    parameters:
      - in: body
        name: blind_search_data
        required: true
        schema:
          type: object
          properties:
            role:
              type: string
              example: Project Manager
            level:
              type: string
              example: средний
            location:
              type: string
              example: Berlin
    responses:
      201:
        description: Данные Слепого поиска успешно сохранены.
      400:
        description: Отсутствуют обязательные поля.
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    # Обязательные поля для Слепого поиска
    target_role = data.get('role')
    target_level = data.get('level')
    location = data.get('location') # Локацию мы будем хранить в focused_skills_data

    if not target_role or not target_level:
        return jsonify({'message': 'Missing role or level'}), 400

    # 1. Находим или создаем основной профиль (ApplicantProfile)
    profile = ApplicantProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = ApplicantProfile(user_id=user_id, identified_role=target_role)
        db.session.add(profile)
        db.session.commit() # Сохраняем, чтобы получить ID профиля

    # 2. Очищаем старые целевые роли (RoleFocus), так как Слепой поиск - это новая цель
    RoleFocus.query.filter_by(profile_id=profile.id).delete()

    # 3. Создаем новую запись RoleFocus
    # Храним роль, уровень и локацию в поле focused_skills_data (для гибкости)
    focus = RoleFocus(
        profile_id=profile.id,
        target_role=target_role,
        target_level=target_level,
        focused_skills_data=json.dumps({'location': location})
    )
    db.session.add(focus)

    try:
        db.session.commit()
        return jsonify({'message': 'Blind profile saved successfully'}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Database error: {e}")
        return jsonify({'message': 'An error occurred while saving the profile'}), 500


# Маршрут, который принимает список навыков для матчинга, для исключения и сохраняет их в таблицах Skill и ApplicantProfile.
@app.route('/api/profile/skills/full', methods=['POST'])
@jwt_required()
def save_full_skills():
    """
    Сохранение полного набора навыков соискателя (100% дата сет)
    и списка исключаемых навыков для текущей цели поиска.
    ---
    tags:
      - Профиль
    security:
      - Bearer: []
    parameters:
      - in: body
        name: skills_data
        required: true
        schema:
          type: object
          properties:
            skills:
              type: array
              items:
                type: string
              description: Полный список включаемых навыков.
            excluded_skills:
              type: array
              items:
                type: string
              description: Список навыков, которые нужно исключить из матчинга.
    responses:
      200:
        description: Навыки успешно обновлены.
      400:
        description: Отсутствуют навыки в списке.
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    skills_list = data.get('skills', [])
    excluded_skills_list = data.get('excluded_skills', [])

    if not skills_list:
        return jsonify({'message': 'Skills list cannot be empty'}), 400

    try:
        # 1. Находим/создаем основной профиль (ApplicantProfile)
        profile = ApplicantProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = ApplicantProfile(user_id=user_id, identified_role="Manual Skill Set")
            db.session.add(profile)
            db.session.flush()

        # 2. Обновление полного набора навыков (100% дата сет)
        profile.skills.clear()
        for skill_name in skills_list:
            skill = Skill.query.filter_by(name=skill_name).first()
            if not skill:
                skill = Skill(name=skill_name)
                db.session.add(skill)

            profile.skills.append(skill)

        # 3. Сохранение исключаемых навыков в RoleFocus

        # Удаляем старую цель (фокус), так как это новая настройка
        RoleFocus.query.filter_by(profile_id=profile.id).delete()

        # Формируем JSON для RoleFocus, включая список исключений
        focus_data_json = json.dumps({
            'excluded_skills': excluded_skills_list,
            'location': 'N/A' # Заглушка, если локация не была выбрана
        })

        # Создаем новую запись RoleFocus
        focus = RoleFocus(
            profile_id=profile.id,
            target_role='Manual Skill Set',  # Временная роль для этого режима
            target_level='All',
            focused_skills_data=focus_data_json
        )
        db.session.add(focus)

        db.session.commit()
        return jsonify({'message': 'Full skill set and exclusions updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving full skill set: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500


