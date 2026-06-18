# URI schemes

The `inputs` and `outputs` in a [manifest](manifest-format.md) reference data
through URIs. SimDB understands two schemes: `file` for ordinary files and
`imas` for IMAS data entries.

## `file` scheme

For ordinary files on the machine where you run the CLI:

```
file:///<absolute-path>
```

Notes:

- The path must be absolute (note the three slashes: `file://` + `/path`).
- Glob patterns are expanded, so `file:///data/run42/*.nc` references every
  matching file.
- `$MANIFEST_DIR` (the directory containing the manifest) and `~` are expanded
  before the path is resolved.

Examples:

```text
file:///work/sims/run42/input/parameters.txt
file:///work/sims/run42/results/*.nc
```

## `imas` scheme

IMAS URIs locate an IMAS data entry. They come in two forms: local and remote.

### Local IMAS data

For an IMAS data entry accessible from the machine running the CLI:

```
imas:<backend>?path=<path>
```

| Part | Description |
| --- | --- |
| `backend` | Backend used to open the data, for example `hdf5` or `mdsplus`. |
| `path` | Path to the folder containing the IMAS data files. |

Alternatively, an entry can be addressed by shot, run, and database instead of a
path: `imas:<backend>?shot=<shot>&run=<run>&database=<database>`.

Examples:

```text
imas:mdsplus?path=/work/imas/shared/imasdb/iter/3/135011/2
imas:hdf5?path=/work/imas/shared/imasdb/ITER_SCENARIOS/3/131002/60
```

When a local IMAS URI is pushed to a server, SimDB rewrites it as a remote data
URI so the data can be reached from machines other than yours. The server's
`imas_remote_host`/`imas_remote_port` settings control this rewrite (see
[Server configuration](server-configuration.md)).

### Remote IMAS data

For an IMAS data entry hosted on a remote data server (for example a UDA
server):

```
imas://<server>:<port>/uda?path=<path>&backend=<backend>
```

| Part | Description |
| --- | --- |
| `server` | Hostname of the remote data server, for example `uda.iter.org`. |
| `port` | Port to connect to. Optional; a default is used if omitted. |
| `path` | Path to the data on the remote server. |
| `backend` | Backend used to open the data. |

Examples:

```text
imas://uda.iter.org:56565/uda?path=/work/imas/shared/imasdb/ITER/3/131024/51&backend=hdf5
imas://uda.iter.org/uda?path=/work/imas/shared/imasdb/ITER/3/131024/51&backend=hdf5
```

```{note}
Make sure the chosen port is reachable through your network firewall. If a
remote IMAS URI cannot be reached, contact your system administrator. See also
[Troubleshooting](../troubleshooting.md).
```

```{note}
SimDB uses [imas-python](https://pypi.org/project/imas-python/) to read IMAS
data. MDSplus data must have been written with Access Layer 5 (AL5) or later;
Access Layer 4 (AL4) data must be migrated first. See
[Migrate AL4 MDSplus data](../how-to/migrate-al4-mdsplus.md).
```

## `simdb` scheme (internal)

SimDB also uses a `simdb:<uuid>` scheme internally to reference a simulation
already registered in the catalogue. This scheme is not used in manifests; you
do not need to write it by hand.
