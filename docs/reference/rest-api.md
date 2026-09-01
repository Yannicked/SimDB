# REST API

A SimDB server exposes a versioned REST API over HTTPS. The CLI talks to this
API for you, so most users never call it directly. This page is for people
integrating with the server or developing against it.

## API versioning

The API is versioned so the server and clients can evolve without breaking each
other. Each version is a complete, self-contained copy of the API, served under
its own path prefix: `/v1`, `/v1.1`, `/v1.2`, and so on. One server can expose
several versions at the same time.

The root URL of a server lists every version it offers. When the CLI connects it
reads that list and selects the **highest** version available, then uses it for
the whole session. Older versions stay mounted so that older clients keep
working against the same server.

| Version | Status | Notes |
| --- | --- | --- |
| v1 | Legacy | Original API. |
| v1.1 | Legacy | Incremental additions over v1. |
| v1.2 | Current | Adds the `staging_dir` endpoint and range query operators (`agt`, `age`, `alt`, `ale`). |
| v1.3 | In development | Adds endpoints for Celery-based background workers (asynchronous processing). Not yet released. |

```{note}
**Adding a version (for API developers).** A new API version must expose the
*complete* API, not only the endpoints that changed. A client selects the single
highest version a server advertises and talks only to that version; there is no
per-endpoint fallback to an older version, so any endpoint missing from the new
version disappears for clients that select it. When you introduce a version,
carry every namespace and top-level route from the previous version forward
alongside your additions. In the code, each version's `Api` under
`src/simdb/remote/apis/<version>/` re-registers the full namespace set
(`simulations`, `files`, `metadata`, `watchers`) plus the shared top-level
routes.
```

## Interactive documentation (Swagger)

Each version publishes interactive Swagger UI documentation that lists every
endpoint and lets you try requests:

- Local development server: <http://localhost:5000/v1.2/docs>
- ITER: <https://simdb.iter.org/scenarios/api/v1.2/docs>

The root URL of a server returns the list of available API URLs as JSON.

## Endpoints

Most endpoints are grouped into resource namespaces:

| Namespace | Purpose |
| --- | --- |
| `simulations` | Create, query, retrieve, push/pull, and trace simulations. |
| `files` | Upload and download simulation data files. |
| `metadata` | Query simulation metadata. |
| `watchers` | Manage watchers on a simulation. |

A few endpoints sit at the top level of each version rather than in a namespace:

| Endpoint | Purpose |
| --- | --- |
| `token` | Issue authentication tokens. |
| `validation_schema` | Retrieve the server's validation schema. |
| `upload_options` | Report whether the server copies uploaded files and IDS data (`copy_files`/`copy_ids`). |
| `staging_dir` | Return the staging directory for an upload (v1.2 and later). |
| `simulation/{id}/data` | Read one IDS field from a simulation's IMAS output, optionally converted to a given Data Dictionary version (v1.3 and later). |

The root URL of a version lists its available endpoints as JSON.

## Authentication

Requests are authenticated according to the server's configured method (token,
LDAP, Active Directory, or a firewall in front of the server). Token-based
authentication issues a JWT from the token endpoint, which the CLI stores per
remote. See [Authenticate](../how-to/authenticate.md) and the server's
[authentication configuration](server-configuration.md#authentication).

## Checking a server from the CLI

```bash
simdb remote SERVER version   # server SimDB version
simdb remote SERVER test      # validate connectivity and auth
simdb remote SERVER directory # storage directory (API >= 1.2)
```
