from flask import Flask
from flask_mysqldb import MySQL
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.jinja_env.globals['STATIC_PREFIX'] = '/static/'
mysql = MySQL(app)
db = SQLAlchemy(app)
# migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'

import routes, models

if __name__ == '__main__':
    app.debug = True
    app.run()
