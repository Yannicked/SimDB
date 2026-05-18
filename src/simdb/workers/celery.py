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

    return celery_app


celery_app = make_celery()
