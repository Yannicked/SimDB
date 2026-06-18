# Install a server

This guide installs SimDB with the server components. For running it, see
[Run a development server](run-dev-server.md) and
[Run behind Nginx and Gunicorn](run-behind-nginx-gunicorn.md).

## Install

Clone SimDB and create a virtual environment:

```bash
git clone https://github.com/iterorganization/SimDB.git
cd SimDB
python3 -m venv venv
source venv/bin/activate
```

Install with the `all` extra (server, PostgreSQL, and IDS validation):

```bash
pip install -e ".[all]"
```

To install only what you need, combine the relevant
[extras](../../getting-started/installation.md#optional-extras), for example
`pip install -e ".[server,postgres]"`.

Verify:

```bash
simdb --version
```

## Create the server configuration

The server reads `app.cfg` from the application configuration directory. Find
it with:

```bash
dirname "$(simdb config path)"
```

On Linux this is typically `/home/$USER/.config/simdb`; on macOS,
`/Users/$USER/Library/Application Support/simdb`.

Create `app.cfg` there with the settings for your deployment, and set its
permissions to owner-only:

```bash
chmod 600 app.cfg
```

A minimal SQLite configuration:

```ini
[flask]
secret_key = CHANGE_ME_TO_A_LONG_RANDOM_STRING

[server]
upload_folder = /var/lib/simdb/simulations
admin_password = CHANGE_ME

[database]
type = sqlite

[authentication]
type = None
```

See the [server configuration reference](../../reference/server-configuration.md)
for every option, including authentication, validation, caching, email, and
roles, and for a PostgreSQL example.

```{tip}
To stand up a complete server (with PostgreSQL and Redis) in one command, use
the [Docker Compose deployment](run-with-docker.md) instead of installing by
hand.
```

## Next steps

- [Run with Docker Compose](run-with-docker.md) for an all-in-one deployment.
- [Set up PostgreSQL](set-up-postgresql.md) for production.
- [Configure authentication](configure-authentication.md).
- [Configure validation](configure-validation.md).
- [Run behind Nginx and Gunicorn](run-behind-nginx-gunicorn.md) for production.
