import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'its-a-secret'
    SQLALCHEMY_DATABASE_URI = 'mysql://s402833:gy13bmrsfq81@127.0.0.1:5001/s402833'

    MYSQL_HOST = '127.0.0.1'
    MYSQL_USER = 's402833'
    MYSQL_PASSWORD = 'gy13bmrsfq81'
    MYSQL_DB = 's402833'
    MYSQL_PORT = 5001
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/images/avatars'