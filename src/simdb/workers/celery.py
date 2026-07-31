from typing import Optional

from celery import Celery

from simdb.config import Config


def make_celery(config: Optional[Config] = None) -> Celery:
    if config is None:
        config = Config()
        config.load()

    broker_url = config.get_string_option(
        "celery.broker_url", default="redis://localhost:6379/0"
    )
    result_backend = config.get_string_option(
        "celery.result_backend", default="redis://localhost:6379/0"
    )

    celery_app = Celery(
        "simdb",
        broker=broker_url,
        backend=result_backend,
        include=["simdb.workers.tasks"],
    )

    # Fail hung ingestion tasks rather than letting them run forever. When the
    # soft limit is hit the task raises SoftTimeLimitExceeded, which the
    # ingestion tasks catch and turn into a terminal COPY_FAILED status. The hard
    # limit is an absolute backstop that forcibly kills the task.
    celery_app.conf.task_soft_time_limit = config.get_int_option(
        "celery.task_soft_time_limit", default=3600
    )
    celery_app.conf.task_time_limit = config.get_int_option(
        "celery.task_time_limit", default=3660
    )

    # Periodically fail simulations left stuck in a non-terminal ingestion state
    # (e.g. because a worker was hard-killed and its task never ran to
    # completion). Runs on the beat scheduler; see fail_stale_ingestions_task.
    celery_app.conf.beat_schedule = {
        "fail-stale-ingestions": {
            "task": "simdb.workers.tasks.fail_stale_ingestions_task",
            "schedule": float(
                config.get_int_option("celery.stale_sweep_interval", default=300)
            ),
        }
    }

    return celery_app


celery_app = make_celery()
