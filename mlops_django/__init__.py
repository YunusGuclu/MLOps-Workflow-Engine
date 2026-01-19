# Django projesi açılışında Celery uygulamasını yüklemek için
from .celery import app as celery_app

__all__ = ('celery_app',)