from pathlib import Path

from simdb.remote.core.typing import current_app


def create_alias_dir(simulation):
    base_dir = Path(current_app.simdb_config.get_option("server.upload_folder"))

    aliases_dir = base_dir / "aliases"
    # Make sure the aliases directory exists
    aliases_dir.mkdir(parents=True, exist_ok=True)

    alias_path = aliases_dir / Path(simulation.alias)
    if not alias_path.exists():
        alias_path.mkdir(parents=True, exist_ok=True)

        (base_dir / simulation.uuid.hex).symlink_to(alias_path)
