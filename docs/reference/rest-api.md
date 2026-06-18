# REST API

A SimDB server exposes a versioned REST API over HTTPS. The CLI talks to this
API for you, so most users never call it directly. This page is for people
integrating with the server or developing against it.

## Versions

The API is versioned. The current version is **v1.2**; clients require a server
that is compatible with `1.2.x`.

| Version | Status | Notes |
| --- | --- | --- |
| v1 | Legacy | Original API. No new features. |
| v1.1 | Legacy | Incremental additions over v1. |
| v1.2 | Current | Adds a staging-directory endpoint and array query operators (`agt`, `age`, `alt`, `ale`). |

## Interactive documentation (Swagger)

Each version publishes interactive Swagger UI documentation that lists every
endpoint and lets you try requests:

- Local development server: <http://localhost:5000/v1.2/docs>
- ITER: <https://simdb.iter.org/scenarios/api/v1.2/docs>

The root URL of a server returns the list of available API URLs as JSON.

## Endpoint groups

Within a version, endpoints are grouped by resource:

| Group | Purpose |
| --- | --- |
| `simulations` | Create, query, retrieve, push/pull, and trace simulations. |
| `files` | Upload and download simulation data files. |
| `metadata` | Query simulation metadata. |
| `watchers` | Manage watchers on a simulation. |
| `validation_schema` | Retrieve the server's validation schema. |
| `token` | Issue authentication tokens. |

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
