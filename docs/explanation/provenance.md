# Provenance

**Provenance** is the record of the environment a simulation ran in. Capturing
it makes a run easier to understand and reproduce later: which platform, which
Python, which environment variables were in effect.

## Capturing provenance

The `simdb provenance` command inspects the current system and writes a
provenance file:

```bash
simdb provenance provenance.yaml
```

The file records:

- **Platform details** such as the operating system, release, machine
  architecture, processor, and Python version.
- **Environment variables** in effect at the time, with `PATH` captured as a
  list of entries.

Run this on the machine and in the environment where the simulation was
produced, so the captured details reflect that run.

## How it fits in

Provenance complements the [manifest](../reference/manifest-format.md): the
manifest says *what* the simulation is and *which data* it produced, while
provenance says *where and how* it was run. Together with metadata and
checksums, provenance supports the broader goal of making catalogued
simulations trustworthy and reproducible.
