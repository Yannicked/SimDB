# Glossary

```{glossary}
Alias
  A human-readable, URL-safe, unique name for a simulation, used instead of its
  UUID. See [Alias](../reference/manifest-format.md#alias).

Access Layer (AL)
  The IMAS data access layer. SimDB reads data written with Access Layer 5
  (AL5) or later. Older Access Layer 4 (AL4) MDSplus data must be migrated
  first. See [Migrate AL4 MDSplus data](../how-to/migrate-al4-mdsplus.md).

Backend
  The storage format used for an IMAS data entry, for example `hdf5` or
  `mdsplus`. Specified in an [IMAS URI](../reference/uri-schemes.md).

Cerberus
  The Python library SimDB uses to validate simulation metadata against a
  server's schema. See [Validation](validation.md).

Checksum
  A hash recorded for each data file (SHA-1 for ordinary files, a content hash
  for IMAS data) used to detect changes. See [Validation](validation.md).

HDF5
  A file-based storage format, usable as an IMAS backend (`imas:hdf5?...`).

IDS
  Interface Data Structure. The standardized data structure used by IMAS to
  represent physics quantities.

IMAS
  Integrated Modelling and Analysis Suite. The data framework used by ITER and
  the wider fusion community. SimDB reads IMAS data through
  [imas-python](https://pypi.org/project/imas-python/).

Manifest
  A YAML file describing a simulation and the data it is associated with, used
  to ingest the simulation. See the
  [manifest format](../reference/manifest-format.md).

MDSplus
  A data system usable as an IMAS backend (`imas:mdsplus?...`).

Metadata
  Searchable key/value information attached to a simulation. See
  [Concepts](concepts.md#metadata).

Remote
  A configured SimDB server that the client can push to and query. See
  [Configure remotes](../how-to/configure-remotes.md).

Simulation
  The central SimDB entity: one run or analysis, with a UUID, optional alias,
  status, files, and metadata. See [Concepts](concepts.md#simulation).

Summary IDS
  An IDS holding condensed summary information about a simulation, a common
  source of metadata.

UDA
  Universal Data Access. A server protocol for reaching remote IMAS data, used
  in [remote IMAS URIs](../reference/uri-schemes.md#remote-imas-data).

UUID
  The permanent unique identifier assigned to every simulation.

Watcher
  A user subscribed to notifications about a simulation. See
  [Concepts](concepts.md#watchers).
```
