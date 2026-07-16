"""
Task runner module that dispatches tasks either to Celery (production) or
executes them synchronously in-process (development).

Usage:
    from app.workers.task_runner import run_task
    run_task("process_session", session_id)
    run_task("retrain_persona", subject_id)
"""
import asyncio
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from synchronous code, handling event-loop edge cases."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an already-running event loop (e.g. FastAPI).
        # Schedule the coroutine on a new thread to avoid blocking.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            future.result()  # block until done
    else:
        asyncio.run(coro)


def run_task(task_name: str, *args, **kwargs):
    """
    Dispatch a background task.

    In development mode (DEVELOPMENT_MODE=true), the task's business logic is
    executed synchronously in-process — no Redis or Celery required.

    In production mode, the task is dispatched via Celery's .delay().
    """
    settings = get_settings()

    if settings.development_mode:
        logger.info(f"[DEV MODE] Running task '{task_name}' synchronously with args={args}")
        _run_task_sync(task_name, *args, **kwargs)
    else:
        logger.info(f"[PROD MODE] Dispatching task '{task_name}' to Celery with args={args}")
        _run_task_celery(task_name, *args, **kwargs)


def _run_task_sync(task_name: str, *args, **kwargs):
    """Execute the task's async business logic directly (no Celery, no Redis)."""
    if task_name == "process_session":
        from app.workers.process_session import _process_session_async
        _run_async(_process_session_async(*args, **kwargs))

    elif task_name == "retrain_persona":
        from app.workers.retrain_persona import _retrain_persona_async
        _run_async(_retrain_persona_async(*args, **kwargs))

    else:
        raise ValueError(f"Unknown task: {task_name}")


def _run_task_celery(task_name: str, *args, **kwargs):
    """Dispatch the task via Celery .delay()."""
    if task_name == "process_session":
        from app.workers.process_session import process_session_task
        process_session_task.delay(*args, **kwargs)

    elif task_name == "retrain_persona":
        from app.workers.retrain_persona import retrain_persona_task
        retrain_persona_task.delay(*args, **kwargs)

    else:
        raise ValueError(f"Unknown task: {task_name}")
