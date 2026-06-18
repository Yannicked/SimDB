# Validate a simulation

Validating checks that a simulation is intact and meets a server's
requirements, before you push it. For the concepts behind validation, see
[Validation](../explanation/validation.md).

## Validate against a server

```bash
simdb simulation validate SIM_ID
simdb simulation validate REMOTE SIM_ID    # name a specific remote
```

A `validation successful` message means the simulation is ready to
[push](push-pull.md).

## Common failures and fixes

### A data source is missing or changed

Validation recomputes the checksum of every input and output and compares it to
what was recorded at ingest. A mismatch (or a missing file) fails validation.

Fix: restore the file, or re-ingest the simulation from an updated manifest so
the recorded checksums match the current data.

### Missing required metadata

A server can require specific metadata. See what it requires:

```bash
simdb remote schema -d 10
```

Fix: add the required fields. For a not-yet-pushed local simulation you can add
metadata with `simdb simulation modify SIM_ID --set-meta NAME=VALUE`, or correct
the manifest and re-ingest. See
[Ingest and manage](ingest-and-manage.md#modify-metadata).

## Server-side validation

Servers can also validate automatically on upload (checksums, metadata schema,
and optional file-content validation such as the IDS validator). This is
controlled by the server's `[validation]` and `[file_validation]` settings; see
[Configure validation](operate-server/configure-validation.md).
