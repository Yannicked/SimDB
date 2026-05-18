import click

from simdb.workers.celery import celery_app


@click.group()
def cli():
    """SimDB Celery worker management."""
    pass


@cli.command()
@click.option(
    "--concurrency",
    type=int,
    default=None,
    help="Number of concurrent worker processes",
)
@click.option(
    "--loglevel",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Logging level",
)
@click.option(
    "--hostname",
    default=None,
    help="Set custom hostname (worker@FQHN)",
)
@click.option(
    "--queues",
    default=None,
    help="Comma-separated list of queues to consume from",
)
def worker(concurrency, loglevel, hostname, queues):
    """Start a Celery worker."""
    argv = ["worker", "--loglevel", loglevel]
    if concurrency is not None:
        argv.extend(["--concurrency", str(concurrency)])
    if hostname is not None:
        argv.extend(["--hostname", hostname])
    if queues is not None:
        argv.extend(["--queues", queues])
    celery_app.worker_main(argv)


@cli.command()
@click.option(
    "--loglevel",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Logging level",
)
@click.option(
    "--schedule-file",
    default="celerybeat-schedule",
    help="Path to the schedule file",
)
@click.option(
    "--max-interval",
    type=int,
    default=300,
    help="Maximum interval between iterations (seconds)",
)
def beat(loglevel, schedule_file, max_interval):
    """Start the Celery beat scheduler."""
    celery_app.start(
        [
            "beat",
            "--loglevel",
            loglevel,
            "--schedule",
            schedule_file,
            "--max-interval",
            str(max_interval),
        ]
    )


if __name__ == "__main__":
    cli()
