# Query operators

`simdb simulation query` (local) and `simdb remote query` (remote) find
simulations by matching against their [metadata](manifest-format.md#metadata).
This page lists the available comparison operators. For worked examples, see
[Query simulations](../how-to/query-simulations.md).

## Constraint syntax

Each constraint has the form:

```
NAME=[modifier:]VALUE
```

- `NAME` is the metadata field to match. Nested fields use dotted names, for
  example `code.name`.
- `modifier` is one of the operators below. If omitted, equality (`eq`) is used.
- String comparisons are case-insensitive.
- Passing several constraints matches simulations that satisfy **all** of them
  (logical AND).

```bash
simdb simulation query code.name=SOLPS-ITER
simdb simulation query pulse=gt:1000 run=0
simdb remote iter query machine=ITER
```

## Operators

These operators are available for both local and remote queries:

| Modifier | Meaning |
| --- | --- |
| `eq` | Equal to `VALUE` (the default when no modifier is given). |
| `ne` | Not equal to `VALUE`. |
| `in` | Field contains `VALUE` (substring match). |
| `ni` | Field does not contain `VALUE`. |
| `gt` | Greater than `VALUE`. |
| `ge` | Greater than or equal to `VALUE`. |
| `lt` | Less than `VALUE`. |
| `le` | Less than or equal to `VALUE`. |
| `exist` | The field exists, regardless of its value. Provide no value: `NAME=exist:`. |

### Array operators (remote only)

When a metadata value is an array, these operators match if **any** element
satisfies the comparison. They are available on remote queries:

| Modifier | Meaning |
| --- | --- |
| `agt` | Any element greater than `VALUE`. |
| `age` | Any element greater than or equal to `VALUE`. |
| `alt` | Any element less than `VALUE`. |
| `ale` | Any element less than or equal to `VALUE`. |

## Examples

```bash
# Exact match (eq is implied)
simdb simulation query responsible_name=j.smith

# Substring match, case-insensitive
simdb simulation query workflow.name=in:test

# Numeric comparison combined with an exact match
simdb simulation query pulse=gt:1000 run=0

# Simulations that have a "sequence" metadata field at all
simdb simulation query sequence=exist:

# Remote array query: any time slice above 5.0
simdb remote iter query time=agt:5.0
```

Use `-m/--meta-data NAME` to add extra metadata columns to the output, and
`--uuid` to include the simulation UUID. See the [CLI reference](cli.md) for all
options.
