# Query simulations

You can search by metadata both in your local catalogue and on a remote server.
The common cases are shown below; for the full operator list and syntax, see
[Query operators](../reference/query-operators.md).

## Query locally

```bash
simdb simulation query code.name=JETTO
simdb simulation query pulse=gt:1000 run=0
```

Each constraint is `NAME=[modifier:]VALUE`. Multiple constraints are combined
with AND. Add metadata columns with `-m` and UUIDs with `--uuid`:

```bash
simdb simulation query machine=ITER -m code.name --uuid
```

## Query a remote

The same syntax works against a server. Remote queries additionally support the
array operators (`agt`, `age`, `alt`, `ale`):

```bash
simdb remote query machine=ITER
simdb remote iter query code.name=SOLPS-ITER
```

If you have set a default remote, omit its name. Example output:

```text
alias     code.name
--------------------
103027/3  SOLPS-ITER
103028/3  SOLPS-ITER
```

## Browse a remote

List everything on a remote, or inspect one simulation:

```bash
simdb remote list
simdb remote info SIM_ID
```

## Common operators

| Constraint | Matches |
| --- | --- |
| `machine=ITER` | exactly `ITER` (case-insensitive) |
| `code.name=in:sol` | values containing `sol` |
| `pulse=gt:1000` | values greater than 1000 |
| `sequence=exist:` | simulations that have a `sequence` field |

See [Query operators](../reference/query-operators.md) for the rest.
