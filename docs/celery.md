# Celery async task processing

SimDB uses [Celery](https://docs.celeryproject.org/) to run asynchronous background
tasks such as copying simulation files and completing the ingestion pipeline.

## Overview

When simulations are uploaded via the REST API, the server offloads heavy operations
to Celery workers instead of blocking the HTTP request. Tasks are defined in
`src/simdb/workers/tasks.py`:

- `copy_files_task` — copies input/output files from source locations to the server's
  upload folder and updates the simulation's ingestion status.
- `complete_ingestion_task` — marks a simulation as fully ingested.
- `validate_imas_task` — runs validation checks on IMAS data (placeholder).
- `send_email_task` — sends email notifications.

Tasks can be chained in the API endpoint:

```python
copy_files = copy_files_task.si(simulation.uuid, ...)
complete = complete_ingestion_task.si(simulation.uuid)
_ = (copy_files | complete).apply_async()
```

## Configuration

Celery is configured via `app.cfg`:

| Section | Option         | Required | Description                                      |
|---------|----------------|----------|--------------------------------------------------|
| celery  | broker_url     | no       | Redis URL for the message broker. Defaults to `redis://localhost:6379/0` |
| celery  | result_backend | no       | Redis URL for results storage. Defaults to `redis://localhost:6379/0`   |

Example:

```ini
[celery]
broker_url = redis://localhost:6379/0
result_backend = redis://localhost:6379/0
```

## Running workers

### Standalone worker

Start a Celery worker using the built-in CLI:

```bash
simdb_worker
```

### Worker with beat scheduler

For periodic tasks (e.g. cleanup, reports), run both the worker and beat:

```bash
# Terminal 1: worker
simdb_worker

# Terminal 2: beat scheduler
simdb_beat
```

### Flower monitoring

[Flower](https://flower.readthedocs.io/) provides a web UI for monitoring Celery
workers and tasks:

```bash
celery -A simdb.workers.celery flower --port=5555
```

## Testing with eager mode

In tests, set `task_always_eager = True` to run tasks synchronously without a
broker.
