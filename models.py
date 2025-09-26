from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'


# модель JobResource для хранения информации о внешних job search API
class JobResource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    base_url = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    api_key_required = db.Column(db.Boolean, default=False)

    def to_dict(self):
        # Используется для отправки данных на фронтенд
        return {
            'id': self.id,
            'name': self.name,
            'is_active': self.is_active
        }


