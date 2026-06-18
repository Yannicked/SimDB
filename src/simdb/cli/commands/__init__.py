from typing import Iterable

import click

from simdb.config import SimDBSettings

pass_config = click.make_pass_decorator(SimDBSettings)


def check_meta_args(args: Iterable[str]):
    for arg in args:
        if "=" in arg:
            click.ClickException(
                f"Invalid additional meta-data field {arg}, must not contain ="
            )
