# Migrate AL4 MDSplus data

SimDB reads IMAS data with
[imas-python](https://pypi.org/project/imas-python/), which requires MDSplus
data written with **Access Layer 5 (AL5)** or later. It cannot read older
**Access Layer 4 (AL4)** MDSplus data. If your data is AL4, migrate it to the
AL5 directory layout before referencing it in a manifest.

## Migrate with `mdsplusIMASDB4to5`

Use the `mdsplusIMASDB4to5` tool provided by IMAS-Core. It creates the AL5
directory layout with links to your original files; the original data is not
removed.

```text
mdsplusIMASDB4to5 [-h] [--dry-run] [-p PATH] [-d DATABASE] [-f]
```

| Option | Description |
| --- | --- |
| `--dry-run` | Print the actions without performing them. |
| `-p PATH`, `--path PATH` | Path of the imasdb to map (default `$HOME/public`). |
| `-d DATABASE`, `--database DATABASE` | A specific database to map (default: all). |
| `-f`, `--force` | Create the symlink even if the target file exists. |

Do a dry run first to see what it would change:

```bash
mdsplusIMASDB4to5 --dry-run -p /path/to/imasdb
```

## Reference the migrated data

Once migrated, reference the new AL5 path in your manifest using the `mdsplus`
backend:

```yaml
outputs:
  - uri: imas:mdsplus?path=<destination_path>
```

For details of `mdsplusIMASDB4to5`, see the IMAS-Core documentation.
