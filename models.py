from flask_login import UserMixin
from __main__ import db, login
from werkzeug.security import check_password_hash


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(128))
    description = db.Column(db.String(255), default='')
    discount = db.Column(db.Integer, default='0')
    avatar = db.Column(db.String(255), unique=True, default='default/default-avatar.png')
    is_admin = db.Column(db.Boolean, default=0)
    is_banned = db.Column(db.Boolean, default=0)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @login.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def get_id(self):
        return (self.user_id)