from .celery_app import celery_app
import tasks.tasks

__all__ = ("celery_app",)
