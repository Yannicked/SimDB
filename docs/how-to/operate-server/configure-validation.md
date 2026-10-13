# Configure validation

A server can validate simulations automatically when they are uploaded:
checksums, a metadata schema, and optionally the contents of data files. For the
concepts, see [Validation](../../explanation/validation.md).

## Validate uploads automatically

In `app.cfg`:

```ini
[validation]
auto_validate = True
error_on_fail = True
```

- `auto_validate` runs validation (including any file validation) on every
  upload.
- `error_on_fail` rejects simulations that fail. It requires `auto_validate`.

## Require metadata

Create `validation-schema.yaml` in the same directory as `app.cfg`, using
[Cerberus](https://docs.python-cerberus.org/) rules:

```yaml
description:
  required: true
  type: string
machine:
  required: true
  type: string
```

Clients can read the active schema with `simdb remote SERVER schema` and check
against it with `simdb simulation validate`.

## Validate file contents (IDS validator)

To check the contents of IMAS data files, enable a file validator. The
`ids_validator` requires the `imas-validator`
[extra](../../getting-started/installation.md#optional-extras).

```ini
[file_validation]
type = ids_validator
bundled_ruleset = True
apply_generic = True
rule_filter_ids = summary,equilibrium
```

See the
[file validation options](../../reference/server-configuration.md#file_validation)
for the full list, including custom rule directories and ruleset filters.
