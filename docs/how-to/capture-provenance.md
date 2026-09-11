# Capture provenance

Provenance is a record of the system a simulation ran on. Capturing it alongside
your data makes a run reproducible and auditable: you can see the platform,
Python version, and environment variables that were in effect.

## Write a provenance file

Run `simdb provenance` with the path of the file to create:

```bash
simdb provenance provenance.yaml
```

This writes a YAML file describing the current system, with two sections:

- `platform`: architecture, machine, operating system, release, and Python
  version (from Python's `platform` module).
- `environment`: every environment variable currently set. `PATH`-style
  variables are split into lists for readability.

Run it on the same machine and in the same shell session as the simulation, so
the captured environment matches the one that produced the data.

## Include it with a simulation

The provenance file is a regular file, so you can catalogue it as one of a
simulation's inputs in the [manifest](../reference/manifest-format.md):

```yaml
inputs:
  - uri: file:///work/sims/run42/provenance.yaml
```

It is then checksummed and pushed with the rest of the simulation's data.

## Next steps

- [Create a manifest](create-a-manifest.md)
- [Ingest and manage simulations](ingest-and-manage.md)
