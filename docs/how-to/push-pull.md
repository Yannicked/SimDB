# Push and pull simulations

Pushing copies a local simulation up to a server; pulling copies a server
simulation down to your machine. Both need a [configured remote](configure-remotes.md).

## Push

Once a simulation is ingested locally and you are happy with its metadata, push
it to make it available to others:

```bash
simdb simulation push SIM_ID
```

This uploads all metadata and copies every referenced input and output. For
`file` URIs the files are transferred directly; for `imas` URIs SimDB discovers
the files to transfer from the backend in the URI. Files are sent over HTTP.

Validate first to catch problems early (see
[Validate a simulation](validate-a-simulation.md)):

```bash
simdb simulation validate SIM_ID
```

### Replace an earlier simulation

```bash
simdb simulation push SIM_ID --replaces OLD_SIM_ID
```

The previous simulation is marked `deprecated` and gains a `replaced_by`
reference to the new one. Inspect the revision history with
`simdb remote trace SIM_ID`.

### Add a watcher while pushing

```bash
simdb simulation push SIM_ID --add-watcher
```

See [watchers](../explanation/concepts.md#watchers) and the
`simdb remote watcher` commands in the [CLI reference](../reference/cli.md).

## Pull

Pull copies a simulation's metadata into your local catalogue and downloads its
data into a directory you choose:

```bash
simdb simulation pull REMOTE SIM_ID DIRECTORY
```

- `REMOTE` is optional; the default remote is used if omitted.
- `SIM_ID` is the alias or UUID on the remote.
- `DIRECTORY` is where the data is downloaded.

After pulling, the simulation appears in your local
[queries](query-simulations.md).
