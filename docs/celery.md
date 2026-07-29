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
- `fail_stale_ingestions_task` — periodic sweep (run by beat) that marks simulations
  stuck in a non-terminal ingestion state as failed, so they cannot remain stuck
  forever after a worker is hard-killed mid-ingestion. See "Recovering stuck
  ingestions" below.

Tasks can be chained in the API endpoint:

```python
copy_files = copy_files_task.si(simulation.uuid, ...)
complete = complete_ingestion_task.si(simulation.uuid)
_ = (copy_files | complete).apply_async()
```

## Configuration

Celery is configured via `app.cfg`:

| Section | Option                  | Required | Description                                      |
|---------|-------------------------|----------|--------------------------------------------------|
| celery  | broker_url              | no       | Redis URL for the message broker. Defaults to `redis://localhost:6379/0` |
| celery  | result_backend          | no       | Redis URL for results storage. Defaults to `redis://localhost:6379/0`   |
| celery  | task_soft_time_limit    | no       | Seconds before a running task is asked to stop (raises `SoftTimeLimitExceeded`, which ingestion tasks turn into a `COPY_FAILED` status). Defaults to `3600`. |
| celery  | task_time_limit         | no       | Hard limit in seconds; the task is forcibly killed. Defaults to `3660`. |
| celery  | stale_sweep_interval    | no       | How often (seconds) the beat scheduler runs `fail_stale_ingestions_task`. Defaults to `300`. |
| celery  | stale_ingestion_timeout | no       | How long (seconds) a simulation may sit in a non-terminal ingestion state before the sweep fails it. Should be larger than `task_time_limit`. Defaults to `7200`. |

Example:

```ini
[celery]
broker_url = redis://localhost:6379/0
result_backend = redis://localhost:6379/0
task_soft_time_limit = 3600
task_time_limit = 3660
stale_sweep_interval = 300
stale_ingestion_timeout = 7200
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

## Recovering stuck ingestions

A simulation moves through non-terminal ingestion states (`QUEUED`, `COPYING`, ...)
before reaching a terminal one (`COMPLETED`, `COPY_FAILED`, `VALIDATION_FAILED`). A
simulation is only deletable once it reaches a terminal state, so it is important
that it never gets stuck. Three mechanisms guard against this:

1. A task that raises is caught and the simulation is marked `COPY_FAILED`.
2. A task that hangs is stopped by `task_soft_time_limit` and then marked
   `COPY_FAILED` (the hard `task_time_limit` is an absolute backstop).
3. A worker that is hard-killed (SIGKILL, OOM, node reboot) never runs its task's
   error handling, so `fail_stale_ingestions_task` sweeps up any simulation left in a
   non-terminal state longer than `stale_ingestion_timeout`. This requires the beat
   scheduler to be running.

The sweep relies on the `ingestion_status_updated_at` column, which is set on insert
and refreshed on every update, so it reflects how long a simulation has been sitting
in its current state.

As a manual fallback, an admin can force-delete a stuck simulation regardless of its
ingestion state:

```
DELETE /v1.3/simulation/<uuid>?force=true
```

## Testing with eager mode

In tests, set `task_always_eager = True` to run tasks synchronously without a
broker.
