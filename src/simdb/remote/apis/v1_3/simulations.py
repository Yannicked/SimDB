import datetime
from typing import Annotated, Optional

from flask_restx import Namespace, Resource

from simdb.database.models import metadata as models_meta
from simdb.database.models import simulation as models_sim
from simdb.enums import IngestionStatus
from simdb.remote.core.auth import User, requires_auth
from simdb.remote.core.cache import clear_cache
from simdb.remote.core.pydantic_utils import (
    Body,
    pydantic_validate,
)
from simdb.remote.core.typing import current_app
from simdb.remote.models import (
    FileDataList,
    SimulationPostData,
    SimulationPostResponse,
    SimulationStatusResponse,
)
from simdb.workers.tasks import (
    complete_ingestion_task,
    copy_files_task,
)

api = Namespace("simulations", path="/")


def _set_alias(simulation: models_sim.Simulation, alias: Optional[str]):
    if alias is None:
        simulation.alias = simulation.uuid.hex
        return

    character = None
    if alias.endswith("-"):
        character = "-"
    elif alias.endswith("#"):
        character = "#"

    if not character:
        simulation.alias = alias
        return

    aliases = current_app.db.get_aliases(alias)
    last_id = max(
        (int(existing_alias.split(character)[-1]) for existing_alias in aliases),
        default=0,
    )
    next_id = last_id + 1
    simulation.alias = f"{alias}{next_id}"
    simulation.meta.append(models_meta.MetaData("seqid", next_id))


@api.route("/simulations")
class SimulationList(Resource):
    @requires_auth()
    @pydantic_validate(api)
    def post(
        self,
        user: User,
        body: Annotated[SimulationPostData, Body()],
    ) -> SimulationPostResponse:
        simulation_data = body.model_copy(deep=True)

        # Clear the file inputs and outputs.
        # The files will be added by the job.
        simulation_data.simulation.outputs = FileDataList()
        simulation_data.simulation.inputs = FileDataList()
        simulation = models_sim.Simulation.from_data_model(simulation_data.simulation)

        # Simulation Upload (Push) Date
        simulation.datetime = datetime.datetime.now()

        uploaded_by = body.uploaded_by or user.email or user.name or "anonymous"

        simulation.set_meta("uploaded_by", uploaded_by)

        _set_alias(simulation, body.simulation.alias)

        simulation.ingestion_status = IngestionStatus.QUEUED
        current_app.db.insert_simulation(simulation)

        # This job will copy and add the files to the simulation
        copy_files = copy_files_task.si(
            simulation.uuid,
            body.simulation.inputs.model_dump(),
            body.simulation.outputs.model_dump(),
        )

        # The complete job will set simulation.ingestion_status = Completed
        complete = complete_ingestion_task.si(simulation.uuid)

        _ = (copy_files | complete).apply_async()

        result = SimulationPostResponse(ingested=simulation.uuid)

        clear_cache()

        return result


@api.route("/simulation/status/<path:sim_id>")
class SimulationIngestionStatus(Resource):
    @requires_auth()
    @pydantic_validate(api)
    def get(
        self,
        sim_id: str,
        user: User,
    ) -> SimulationStatusResponse:
        simulation = current_app.db.get_simulation(sim_id)
        return SimulationStatusResponse(status=simulation.ingestion_status)
