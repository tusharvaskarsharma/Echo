import os
from app.config import get_settings

settings = get_settings()

if settings.development_mode:
    # In development mode, create a minimal Celery stub so that
    # @celery_app.task decorators still work at import time,
    # but no actual Redis connection is attempted.
    from celery import Celery
    celery_app = Celery("echo_worker")
    celery_app.conf.update(
        task_always_eager=True,       # Execute tasks inline if accidentally called
        task_eager_propagates=True,   # Propagate exceptions in eager mode
        broker_connection_retry_on_startup=False,
    )
else:
    from celery import Celery
    celery_app = Celery(
        "echo_worker",
        broker=os.getenv("REDIS_URL", settings.redis_url),
        backend=os.getenv("REDIS_URL", settings.redis_url),
        include=["app.workers.process_session", "app.workers.retrain_persona"]
    )

    celery_app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )
