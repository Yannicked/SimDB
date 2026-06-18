# Ingest and manage simulations

This guide covers working with simulations in your **local** catalogue:
ingesting, listing, inspecting, modifying metadata, and deleting. For querying,
see [Query simulations](query-simulations.md); for sharing, see
[Push and pull](push-pull.md).

## Ingest

Add a simulation from a [manifest](create-a-manifest.md):

```bash
simdb simulation ingest manifest.yaml
```

Override the manifest's alias at ingest time:

```bash
simdb simulation ingest -a my-alias manifest.yaml
```

## List

```bash
simdb simulation list
```

Useful options:

```bash
simdb simulation list -m machine -m code.name   # add metadata columns
simdb simulation list --uuid                     # show UUIDs
simdb simulation list -l 50                       # limit rows (default 100)
```

## Inspect

Show everything stored for one simulation, by alias or UUID:

```bash
simdb simulation info my-alias
```

## Modify metadata

Add or update, and delete, metadata on a local simulation:

```bash
simdb simulation modify my-alias --set-meta reviewed=yes
simdb simulation modify my-alias --del-meta reviewed
simdb simulation modify my-alias -a new-alias        # change the alias
```

## Delete

Delete a single simulation:

```bash
simdb simulation delete my-alias
```

Reset the entire local catalogue:

```bash
simdb simulation delete --all
```

```{note}
`simdb simulation delete --all` replaces the old `simdb database clear` command,
which has been removed.
```
