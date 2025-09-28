from app import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    date_started = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'


# Модель для хранения информации о соискателе и его резюме
class ApplicantProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)

    # Определенная роль для поиска
    identified_role = db.Column(db.String(100), nullable=True)

    # Хранение текста резюме (если загружено)
    resume_text = db.Column(db.Text, nullable=True)

    date_started = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    # Связь с пользователем
    user = db.relationship('User', backref=db.backref('profile', uselist=False))

    def __repr__(self):
        return f'<Profile {self.identified_role}>'

# Модель для хранения ключевых навыков соискателя (многие ко многим)
class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return f'<Skill {self.name}>'

# Вспомогательная таблица для связи Профиля и Навыков
profile_skills = db.Table('profile_skills',
    db.Column('profile_id', db.Integer, db.ForeignKey('applicant_profile.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True)
)

# Добавить связь в ApplicantProfile для доступа к навыкам
ApplicantProfile.skills = db.relationship(
    'Skill', secondary=profile_skills, lazy='subquery',
    backref=db.backref('profiles', lazy=True)
)


class RoleFocus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('applicant_profile.id'), nullable=False)

    # Роль, на которую сейчас нацелен пользователь (например, 'Tech Support')
    target_role = db.Column(db.String(100), nullable=False)

    # Уровень поиска на этой роли ('начальный', 'средний', 'продвинутый')
    target_level = db.Column(db.String(50), nullable=False)

    # Хранение ID и степени использования навыков в формате JSON/текста (для гибкости)
    # Например: {'Python': 'продвинутый', 'SQL': 'средний', 'Content Creation': 'начальный'}
    focused_skills_data = db.Column(db.Text, nullable=True)

    date = db.Column(db.DateTime, default=datetime.utcnow) # date записывается при создании


    profile = db.relationship('ApplicantProfile', backref=db.backref('role_focuses', lazy=True))

    def __repr__(self):
        return f'<RoleFocus {self.target_role} - {self.target_level}>'


# модель JobResource для хранения информации о внешних job search API
class JobResource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    base_url = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    api_key_required = db.Column(db.Boolean, default=False)
    date_started = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        # Используется для отправки данных на фронтенд
        return {
            'id': self.id,
            'name': self.name,
            'is_active': self.is_active
        }


