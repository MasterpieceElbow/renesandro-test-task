# Configure Celery to use Redis as the message broker
from celery import Celery

from main.settings import settings

celery_app = Celery(
    "worker",
    broker=f"{settings.redis_url}/0",  
    backend=f"{settings.redis_url}/0", 
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,
)
