# Tutorial: push your simulation to a server

This tutorial continues from
[Catalogue your first simulation](first-simulation.md). You have a simulation in
your local catalogue; now you will validate it against a server and push it so
others can find it.

```{note}
ITER users should follow [Connect to ITER](../how-to/connect-to-iter.md) for the
server URL, firewall, and certificate setup, then return here from Step 2.
```

## Step 1: add a remote

A *remote* is a configured SimDB server. List the remotes you already have:

```bash
simdb remote config list
```

Add a server and make it your default so you do not have to name it every time:

```bash
simdb remote config new myserver https://example.org/simdb/api
simdb remote config set-default myserver
```

## Step 2: test the connection

Check the remote is reachable and list what is already on it:

```bash
simdb remote test
simdb remote list
```

You will be asked to authenticate. To avoid re-entering credentials on every
command, see [Authenticate](../how-to/authenticate.md).

## Step 3: validate before pushing

Different servers can require different metadata, so validate your simulation
against the target server first:

```bash
simdb simulation validate iter-baseline-scenario-2024
```

If validation fails, the two usual causes are:

- a data file is missing or its checksum no longer matches (something changed
  since ingestion); or
- the simulation is missing metadata the server requires.

You can see what a server requires with:

```bash
simdb remote schema -d 10
```

Fix any issues (see [Validate a simulation](../how-to/validate-a-simulation.md))
until you get a `validation successful` message.

## Step 4: push

```bash
simdb simulation push iter-baseline-scenario-2024
```

This uploads the metadata and copies all referenced input and output data to the
server. For `file` URIs the files are transferred directly; for `imas` URIs
SimDB discovers the underlying files from the backend.

### Replacing an earlier simulation

If this run supersedes one already on the server:

```bash
simdb simulation push iter-baseline-scenario-2024 --replaces OLD_SIM_ID
```

The previous simulation is marked `deprecated` and gains a `replaced_by`
reference pointing to the new one. Follow the chain of revisions with:

```bash
simdb remote trace iter-baseline-scenario-2024
```

## What you have learned

You configured a remote, validated a simulation against it, and pushed it.
From here:

- [Query simulations](../how-to/query-simulations.md) on the server.
- [Pull simulations](../how-to/push-pull.md) back to your machine.
- [Use the dashboard](../how-to/use-the-dashboard.md) to browse in a browser.
