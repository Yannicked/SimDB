# Configure remotes

A *remote* is a SimDB server the client can talk to. Remotes are stored in your
[client configuration](../reference/configuration.md) file. Manage them with the
`simdb remote config` commands rather than editing the file by hand, so it stays
valid.

ITER users: see [Connect to ITER](connect-to-iter.md) for the ITER-specific
URL, firewall, and certificate setup.

## List remotes

```bash
simdb remote config list
```

## Add a remote

```bash
simdb remote config new NAME URL
```

For example:

```bash
simdb remote config new myserver https://example.org/simdb/api
```

## Set a default

The default remote is used whenever you omit the remote name from a `remote` or
`simulation` command:

```bash
simdb remote config set-default myserver
simdb remote config get-default
```

## Set per-remote options

```bash
simdb remote config set-option myserver username my-user
simdb remote config set-option myserver firewall F5
```

Common options are `url`, `username`, `firewall`, and `default`; see the
[configuration reference](../reference/configuration.md#remote-name).

## Remove a remote

```bash
simdb remote config delete myserver
```

## Test a remote

```bash
simdb remote test            # default remote
simdb remote myserver test   # named remote
simdb remote myserver version
```

Next: set up [authentication](authenticate.md) so you do not have to enter
credentials on every command.
