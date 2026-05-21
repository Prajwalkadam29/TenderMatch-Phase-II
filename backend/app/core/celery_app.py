import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")

from celery.schedules import crontab

celery_app = Celery(
    "tendermatch_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.ingestion_tasks",
        "app.tasks.matching_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.scraper_tasks",
        "app.tasks.scheduled_tasks",
    ]
)

import app.core.celery_db

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes maximum per task
    task_default_queue="default",
    
    # Configure Celery Beat schedules
    beat_schedule={
        "scrape-tendertiger-hourly": {
            "task": "run_automated_scraper",
            "schedule": crontab(minute=0, hour="*"),
        },
        "nightly-bidassist-sync": {
            "task": "nightly_bidassist_sync",
            "schedule": crontab(minute=30, hour=18), # 18:30 UTC -> 11:00 PM IST
        },
        "nightly-portal-scrape": {
            "task": "nightly_portal_scrape",
            "schedule": crontab(minute=0, hour=18), # 18:00 UTC -> 11:30 PM IST (Wait, 18:00 UTC is 11:30 PM IST. 18:00 + 5:30 = 23:30)
        },
    }
)
