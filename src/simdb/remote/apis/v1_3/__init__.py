from flask_restx import Api

from simdb.remote.apis.files import api as file_ns
from simdb.remote.apis.metadata import api as metadata_ns
from simdb.remote.apis.v1_2 import StagingDirectory
from simdb.remote.apis.v1_2 import api as api_v1_2
from simdb.remote.apis.watchers import api as watcher_ns
from simdb.remote.core.auth import TokenAuthenticator

from .simulations import api as sim_ns

api = Api(
    title="SimDB REST API",
    version="1.3",
    description="SimDB REST API",
    authorizations={
        "basicAuth": {
            "type": "basic",
        },
        "apiToken": {
            "type": "apiKey",
            "in": "header",
            "name": TokenAuthenticator.TOKEN_HEADER_NAME,
        },
    },
    security=["basicAuth", "apiToken"],
    doc="/docs",
)

namespaces = [metadata_ns, watcher_ns, file_ns, sim_ns]

api.route("/staging_dir", defaults={"sim_hex": None})(StagingDirectory)
api.route("/staging_dir/<string:sim_hex>")(StagingDirectory)

api.models.update(api_v1_2.models)
