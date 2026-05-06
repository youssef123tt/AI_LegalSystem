"""
Celery application configuration.

WHAT IS CELERY?
---------------
Celery is a distributed task queue.  Think of it as a "to-do list" for
your backend:

1. The API writes a task onto the list (Redis queue).
2. A Celery worker process reads tasks off the list and executes them.

This separation means the API can respond to users quickly while heavy
work (OCR, embedding, etc.) runs in the background.

BROKER vs BACKEND
-----------------
- broker  = where tasks are QUEUED (Redis in our case).
- backend = where task RESULTS are stored (also Redis).
"""

import os

from celery import Celery


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


celery_app = Celery(
    "legal_rag_worker",
    broker=_redis_url(),
    backend=_redis_url(),
)

# Tell Celery where to find task modules.
# Without this line, Celery won't know about process_document.
celery_app.conf.include = ["worker.tasks"]
