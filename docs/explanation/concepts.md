# Concepts

This page explains the ideas behind SimDB and how they fit together. If you just
want to get going, see the [quickstart](../getting-started/quickstart.md); come
back here when you want the bigger picture.

## What SimDB is for

A simulation produces data, but the data alone does not tell you what produced
it, with which code, for which machine, or whether anyone has checked it.
SimDB's job is to **catalogue** simulations: to record metadata about each run
and the data it is associated with, keep that record locally, and let you
publish it to a shared server where others can find, trust, and reuse it.

## Simulation

A **simulation** is the central entity. It represents one run or analysis and
carries:

- a **UUID**, its permanent unique identifier;
- an optional **alias**, a human-readable name;
- a **status** (see [Lifecycle](#status-and-lifecycle));
- lists of **input** and **output** files;
- free-form **metadata** (key/value pairs);
- **watchers** (people notified about changes).

## Manifest

You do not create a simulation by hand. You write a **manifest**, a small YAML
file that describes the simulation and points at its data, and ingest it. The
manifest is the input; the catalogued simulation is the result. See the
[manifest format](../reference/manifest-format.md).

## Files and checksums

Each input and output is tracked as a **file** record with its URI, a type
(an ordinary file, an IMAS entry, or a reference to another simulation), and a
**checksum**. Checksums (a SHA-1 hash for ordinary files, a content hash for
IMAS data) let SimDB detect whether data changed after it was catalogued, which
is the basis of integrity checking during push and validation. See
[Validation](validation.md).

## Metadata

**Metadata** is the searchable description of a simulation: the machine, the
code and version, a free-text description, and any other key/value pairs you
choose. Metadata is what you query on, both locally and on a server, using the
[query operators](../reference/query-operators.md).

## Alias

An **alias** is a friendly name you can use instead of the UUID, for example
`iter-baseline-2024` or `100001/1`. Aliases must be unique within a SimDB
instance and URL-safe, and become fixed once a simulation is pushed. See
[Alias rules](../reference/manifest-format.md#alias).

## Local versus remote

SimDB has two halves:

- **Local catalogue**: a SQLite database on your own machine. Ingesting a
  manifest adds the simulation here, visible only to you.
- **Remote server**: a shared SimDB service (backed by PostgreSQL in
  production). Pushing a simulation copies its metadata and data to the server
  so authorized colleagues can query and reuse it.

A separate distinction applies to the *data* a simulation references:

- **Local IMAS data** is reachable from the file system where you run the CLI.
- **Remote IMAS data** lives on a data server and is reached over the network.

The two distinctions are independent: a locally-catalogued simulation can
reference either local or remote data. When you push, local IMAS URIs are
rewritten so the data stays reachable from the server. See
[URI schemes](../reference/uri-schemes.md).

## Typical workflow

1. Write a manifest describing the simulation and its data.
2. Ingest it into your local catalogue.
3. Manage and inspect it locally; adjust metadata as needed.
4. Validate it against a target server's rules.
5. Push it to the server to share it.

Others can then query the server, pull a simulation back to their own machine,
and download its data.

## Status and lifecycle

On a server, a simulation has a **status** that records where it is in the
review lifecycle:

| Status | Meaning |
| --- | --- |
| `not_validated` | Uploaded but not yet validated. |
| `accepted` | Accepted into the database. |
| `passed` | Passed validation. |
| `failed` | Failed validation. |
| `deprecated` | Superseded by a newer simulation. |
| `deleted` | Marked as deleted. |

When a simulation replaces an earlier one (`simdb simulation push --replaces`),
the old one is marked `deprecated` and gains a `replaced_by` reference. You can
follow this chain of revisions with `simdb remote SERVER trace`.

## Watchers

A **watcher** is a person who has asked to be notified about a simulation. They
can subscribe to validation results, new revisions, obsolescence, or all
events. Watchers are managed with `simdb remote watcher` and notified by email
from the server.
