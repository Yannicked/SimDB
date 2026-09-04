# Authenticate to a remote

Every command that talks to a remote server must be authenticated. By default
you enter a username and password, which you must re-enter whenever your session
expires. Where the server supports it, a token avoids repeated prompts.

```{note}
The commands below assume you have set a [default remote](configure-remotes.md).
If not, insert the remote name: `simdb remote NAME token new`.
```

## Username and password

By default, remote commands prompt for your username and password. Store your
username so only the password is requested:

```bash
simdb remote config set-option NAME username my-user
```

## Token-based authentication

If the server supports tokens, generate one. You authenticate once with your
username and password, and SimDB stores a token for subsequent commands:

```bash
simdb remote token new
```

While the token is valid (the lifetime is set per server, 30 days by default)
you can run remote commands without entering credentials again. Delete a stored
token with:

```bash
simdb remote token delete
```

```{important}
Servers behind an F5 firewall (including the ITER server `simdb.iter.org`)
authenticate at the firewall and do **not** support SimDB tokens. For those, you
authenticate through the firewall on each session. See
[Connect to ITER](connect-to-iter.md).
```

## Where tokens are stored

Tokens are saved against the remote in your
[client configuration](../reference/configuration.md) file, which must be
readable only by you (`0600` permissions). They are masked in
`simdb config list` output.
