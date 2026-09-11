# SimDB simulation management tool

[![PyPI](https://img.shields.io/pypi/v/imas-simdb.svg)](https://pypi.org/project/imas-simdb/)
[![Documentation Status](https://readthedocs.org/projects/simdb/badge/?version=latest)](https://simdb.readthedocs.io/en/latest/)
[![CI](https://github.com/iterorganization/SimDB/actions/workflows/build_and_test.yml/badge.svg)](https://github.com/iterorganization/SimDB/actions)

**SimDB** tracks, manages, validates and shares scientific simulations. You
describe a simulation and its data in a small manifest file, ingest it into your
local catalogue, and push it to a shared SimDB server where colleagues can query,
validate and reuse it. It is built for [IMAS](https://imas.iter.org/)
fusion-simulation workflows.

## Quickstart

SimDB requires Python 3.11 or newer.

```bash
pip install imas-simdb
simdb --version
```

Catalogue a simulation and share it:

```bash
simdb manifest create manifest.yaml      # create and edit a manifest
simdb simulation ingest manifest.yaml    # add it to your local catalogue
simdb simulation push [REMOTE] SIM_ID    # push it to a server
```

Query simulations by metadata:

```bash
simdb simulation query code.name=SOLPS-ITER     # local
simdb remote [REMOTE] query code.name=SOLPS-ITER # on a server
```

See the [quickstart guide](https://simdb.readthedocs.io/en/latest/getting-started/quickstart.html)
for a full walkthrough.

## Documentation

Full documentation is at **[simdb.readthedocs.io](https://simdb.readthedocs.io/en/latest/)**:

- [Installation](https://simdb.readthedocs.io/en/latest/getting-started/installation.html)
- [Tutorial: catalogue your first simulation](https://simdb.readthedocs.io/en/latest/tutorials/first-simulation.html)
- [CLI reference](https://simdb.readthedocs.io/en/latest/reference/cli.html)
- [Connect to ITER](https://simdb.readthedocs.io/en/latest/how-to/connect-to-iter.html)
- [Operating a server](https://simdb.readthedocs.io/en/latest/how-to/operate-server/install-server.html)
- [Developer guide](https://simdb.readthedocs.io/en/latest/how-to/contribute/set-up-dev-env.html)

## License

SimDB is licensed under the **LGPLv3** license. See [LICENSE.txt](LICENSE.txt).

## Contact

- Issues and feature requests: [GitHub Issues](https://github.com/iterorganization/SimDB/issues)
- Documentation: [simdb.readthedocs.io](https://simdb.readthedocs.io/en/latest/)
