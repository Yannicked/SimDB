# Installation

SimDB is distributed as the `imas-simdb` Python package and requires
**Python 3.11 or newer**.

## Install from PyPI

```bash
pip install imas-simdb
```

## Install from source

```bash
git clone https://github.com/iterorganization/SimDB.git
cd SimDB
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Optional extras

The base install gives you the client. Additional features are available as
extras:

| Extra | Installs support for |
| --- | --- |
| `server` | Running a SimDB remote server. |
| `postgres` | PostgreSQL as the server database. |
| `imas-validator` | IDS file-content validation. |
| `auth-ldap` | LDAP authentication (server). |
| `auth-keycloak` | Keycloak authentication (server). |
| `auth-ad` | Active Directory authentication (server). |
| `auth` | All three authentication methods. |
| `build-docs` | Building this documentation. |
| `all` | `server`, `imas-validator`, and `postgres` together. |

Install one or more extras with the usual pip syntax:

```bash
pip install "imas-simdb[server]"
pip install "imas-simdb[server,postgres,imas-validator]"
pip install -e ".[all]"          # from a source checkout
```

## Verify

```bash
simdb --version
simdb --help
```

```{tip}
If you get `command not found: simdb`, the install location's `bin` directory is
not on your `PATH`. Activate your virtual environment, or add the pip script
directory to `PATH`. See [Troubleshooting](../troubleshooting.md).
```

## Next steps

- Run through the [quickstart](quickstart.md).
- Working with ITER servers? See [Connect to ITER](../how-to/connect-to-iter.md).
- Setting up a server? See
  [Install a server](../how-to/operate-server/install-server.md).
