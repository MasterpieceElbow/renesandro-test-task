# Configure Celery to use Redis as the message broker
from celery import Celery

from main.settings import settings

celery_app = Celery(
    "worker",
    broker=f"redis://{settings.redis_host}:{settings.redis_port}/0",  # This is the Redis connection string
    backend=f"redis://{settings.redis_host}:{settings.redis_port}/0",  # Optional, for storing task results
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,
)
