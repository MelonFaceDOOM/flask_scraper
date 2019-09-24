import os
from dotenv import load_dotenv
from celery.schedules import crontab

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMINS = ['lemmyelon@gmail.com']
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')

    BROKER_URL = os.environ.get('REDIS_URL') or \
        "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL') or \
        "redis://localhost:6379/0"

    CELERY_IMPORTS = ('app.scraping.tasks')
    CELERY_TASK_RESULT_EXPIRES = 30
    CELERY_TIMEZONE = 'UTC'

    CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'

    CELERYBEAT_SCHEDULE = {
        'test-celery': {
            'task': 'app.scraping.tasks.rechem_single_page',
            # Every 10 minutes would be "*/10"
            # see scheduling examples here:
            # http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html#entries
            'schedule': crontab(minute="*/10"),
        }
    }
