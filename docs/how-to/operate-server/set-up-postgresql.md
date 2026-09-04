# Set up PostgreSQL

For a production server, use PostgreSQL as the database. This guide covers
installing PostgreSQL, creating the SimDB database, applying migrations, and
pointing the server at it. It is not an exhaustive PostgreSQL guide; see the
[PostgreSQL documentation](https://www.postgresql.org/) for more.

If PostgreSQL is already running, skip to [Create the database](#create-the-database).

## Install PostgreSQL

Install from your system package manager. On RHEL/CentOS:

```bash
sudo yum -y install postgresql-server postgresql-contrib
```

Initialise the database cluster (this creates the default data directory, for
example `/var/lib/pgsql/data`):

```bash
sudo postgresql-setup initdb
```

Start the service and enable it at boot:

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

## Create the database

Connect as the `postgres` user:

```bash
sudo -u postgres psql
```

Create the database and a role for the server (this assumes the server runs as
user `simdb`; change the role name to match your server user):

```sql
CREATE DATABASE simdb;
CREATE ROLE simdb;
ALTER DATABASE simdb OWNER TO simdb;
ALTER ROLE "simdb" WITH LOGIN;
```

## Test the connection

```python
import psycopg2
psycopg2.connect("postgresql://simdb@localhost:5432")
```

```{tip}
If a local connection is refused, check `pg_hba.conf` in the PostgreSQL data
directory and ensure the connection method is `trust` (or another method you can
authenticate with) rather than `ident`.
```

## Apply migrations

The schema is managed with [Alembic](https://alembic.sqlalchemy.org/). Point it
at the database and upgrade to the latest revision:

```bash
export DATABASE_URL="postgresql+psycopg2://simdb@localhost/simdb"
alembic upgrade head
```

See [Run database migrations](../contribute/run-migrations.md) for more.

## Point the server at PostgreSQL

In `app.cfg`:

```ini
[database]
type = postgres
host = localhost
port = 5432
user = simdb
password = simdb
db_name = simdb
```

`user`, `password`, and `db_name` each default to `simdb` if omitted.

The server also needs the PostgreSQL driver, installed by the `postgres`
[extra](../../getting-started/installation.md#optional-extras)
(`pip install -e ".[postgres]"`).
