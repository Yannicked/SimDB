# Quickstart

This page gets you from an installed SimDB to a catalogued, queried, and
(optionally) shared simulation in a few minutes. For a fuller walkthrough, see
the [tutorial](../tutorials/first-simulation.md).

## Prerequisites

- SimDB [installed](installation.md) (`simdb --version` works).

## Step 1: create a manifest

A [manifest](../reference/manifest-format.md) describes your simulation. Start
from a template:

```bash
simdb manifest create manifest.yaml
```

Edit it to point at your data and describe the run:

```yaml
manifest_version: 2
alias: my-first-simulation
inputs:
  - uri: file:///path/to/input/parameters.txt
outputs:
  - uri: file:///path/to/results/output.nc
metadata:
  - machine: ITER
  - code:
      name: JETTO
      version: "2024.1"
  - description: My first catalogued simulation.
```

Check that it is well-formed:

```bash
simdb manifest check manifest.yaml
```

## Step 2: ingest it locally

```bash
simdb simulation ingest manifest.yaml
```

The simulation is now in your local catalogue. List and inspect it:

```bash
simdb simulation list
simdb simulation info my-first-simulation
```

## Step 3: query locally

```bash
simdb simulation query code.name=JETTO
```

See [query operators](../reference/query-operators.md) for the full syntax.

## Step 4: push to a server (optional)

If you have access to a SimDB server, configure it once:

```bash
simdb remote config new myserver https://example.org/simdb/api
simdb remote config set-default myserver
```

Then validate and push:

```bash
simdb simulation validate my-first-simulation
simdb simulation push my-first-simulation
```

ITER users should follow [Connect to ITER](../how-to/connect-to-iter.md)
instead, which covers the firewall and certificate setup.

## Next steps

- [Catalogue your first simulation](../tutorials/first-simulation.md) (tutorial)
- [Create a manifest](../how-to/create-a-manifest.md) (how-to)
- [Concepts](../explanation/concepts.md) (the bigger picture)
