# Configure authentication

A server authenticates users according to its `[authentication]` configuration.
This guide shows the common setups; for every option see the
[server configuration reference](../../reference/server-configuration.md#authentication).

## No authentication (testing only)

```ini
[authentication]
type = None
```

## Behind a firewall

When the server runs behind a firewall (such as F5) that authenticates users and
passes their identity in request headers, read the identity from those headers:

```ini
[authentication]
firewall_auth = True
firewall_user = X-Forwarded-User
firewall_email = X-Forwarded-Email
```

Set `firewall_user` and `firewall_email` to the header names your firewall uses.

## LDAP

Requires the `auth-ldap` [extra](../../getting-started/installation.md#optional-extras).

```ini
[authentication]
type = LDAP
ldap_server = ldaps://ldap.example.org
ldap_bind = uid={username},ou=Users,dc=example,dc=org
ldap_query_base = dc=example,dc=org
ldap_query_filter = (uid={username})
```

`{username}` is replaced with the authenticating user's name. See the
[reference](../../reference/server-configuration.md#ldap-type--ldap) for the
optional query-user, uid, and mail settings.

## Active Directory

Requires the `auth-ad` [extra](../../getting-started/installation.md#optional-extras).

```ini
[authentication]
type = ActiveDirectory
ad_server = ad.example.org
ad_domain = EXAMPLE
ad_cert = /path/to/root-ca.crt
```

## Admin access

The `admin` superuser (password set by `server.admin_password`) and any users in
the `admin` [role](../../reference/server-configuration.md#role-name) can use the
`simdb remote admin` commands:

```ini
[role "admin"]
users = admin,alice,bob
```
