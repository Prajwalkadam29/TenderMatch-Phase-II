import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")

from celery.schedules import crontab

celery_app = Celery(
    "tendermatch_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.document_tasks", "app.tasks.notification_tasks", "app.tasks.scraper_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes maximum per task
    
    # Configure Celery Beat to run the scraper every hour
    beat_schedule={
        "scrape-tendertiger-hourly": {
            "task": "run_automated_scraper",
            "schedule": crontab(minute=0, hour="*"), # Runs at minute 0 past every hour
        },
    }
)
