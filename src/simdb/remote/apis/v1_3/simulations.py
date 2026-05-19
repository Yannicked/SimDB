import datetime
import itertools
from typing import Annotated

from celery.result import AsyncResult
from flask_restx import Namespace, Resource

from simdb.database.models import metadata as models_meta
from simdb.database.models import simulation as models_sim
from simdb.remote.core.auth import User, requires_auth
from simdb.remote.core.cache import clear_cache
from simdb.remote.core.pydantic_utils import (
    Body,
    pydantic_validate,
)
from simdb.remote.core.typing import current_app
from simdb.remote.models import (
    SimulationPostData,
    SimulationPostResponse3,
)
from simdb.workers.tasks import copy_files_task

api = Namespace("simulations", path="/")


def _set_alias(alias: str):
    character = None
    if alias.endswith("-"):
        character = "-"
    elif alias.endswith("#"):
        character = "#"

    if not character:
        return None, -1

    aliases = current_app.db.get_aliases(alias)
    last_id = max(
        (int(existing_alias.split(character)[-1]) for existing_alias in aliases),
        default=0,
    )
    alias = f"{alias}{last_id + 1}"

    return alias, last_id + 1


@api.route("/simulations")
class SimulationList(Resource):
    @requires_auth()
    @pydantic_validate(api)
    def post(
        self,
        user: User,
        body: Annotated[SimulationPostData, Body()],
    ) -> SimulationPostResponse3:
        simulation = models_sim.Simulation.from_data_model(body.simulation)

        # Simulation Upload (Push) Date
        simulation.datetime = datetime.datetime.now()

        uploaded_by = body.uploaded_by or user.email or user.name or "anonymous"

        simulation.set_meta("uploaded_by", uploaded_by)

        alias = body.simulation.alias
        if alias is not None:
            (simulation.alias, next_id) = _set_alias(alias)
            if next_id > -1:
                simulation.meta.append(models_meta.MetaData("seqid", next_id))
        else:
            simulation.alias = simulation.uuid.hex

        files = list(
            itertools.chain(body.simulation.inputs.root, body.simulation.outputs.root)
        )

        simulation.ingestion_status = simulation.IngestionStatus.QUEUED
        current_app.db.insert_simulation(simulation)

        # Start ingestion job with files, return job_id
        job: AsyncResult = copy_files_task.delay(simulation.uuid, files)
        job_id = job.id

        result = SimulationPostResponse3(job_id=job_id)

        
        clear_cache()

        return result
