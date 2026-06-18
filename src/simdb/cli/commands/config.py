import re
from typing import Any

import click

from . import pass_config
from pydantic import BaseModel


def _get_option(config, option_name):
    if "." in option_name:
        parts = option_name.split(".")
        obj = config
        for part in parts:
            norm_part = {
                "remote": "remotes",
                "role": "roles",
                "partition": "partitions",
            }.get(part, part).replace("-", "_")
            
            if isinstance(obj, dict):
                obj = obj[norm_part]
            elif hasattr(obj, norm_part):
                obj = getattr(obj, norm_part)
            else:
                raise KeyError(f"Option {option_name} not found.")
        return obj
    else:
        norm_part = option_name.replace("-", "_")
        if hasattr(config, norm_part):
            return getattr(config, norm_part)
        raise KeyError(f"Option {option_name} not found.")


def _set_option(config, option_name, value):
    if "." in option_name:
        parts = option_name.split(".")
        obj = config
        for part in parts[:-1]:
            norm_part = {
                "remote": "remotes",
                "role": "roles",
                "partition": "partitions",
            }.get(part, part).replace("-", "_")
            
            if isinstance(obj, dict):
                obj = obj[norm_part]
            elif hasattr(obj, norm_part):
                obj = getattr(obj, norm_part)
            else:
                raise KeyError(f"Option {option_name} not found.")
                
        last_part = parts[-1].replace("-", "_")
        if isinstance(obj, dict):
            obj[last_part] = value
        else:
            field_info = obj.model_fields.get(last_part)
            if field_info:
                annotation = field_info.annotation
                if annotation is bool or (hasattr(annotation, "__args__") and bool in annotation.__args__):
                    value = value.lower() in ("true", "1", "yes")
                elif annotation is int or (hasattr(annotation, "__args__") and int in annotation.__args__):
                    value = int(value)
                elif annotation is float or (hasattr(annotation, "__args__") and float in annotation.__args__):
                    value = float(value)
            setattr(obj, last_part, value)
    else:
        norm_part = option_name.replace("-", "_")
        setattr(config, norm_part, value)


def _delete_option(config, option_name):
    if "." in option_name:
        parts = option_name.split(".")
        obj = config
        for part in parts[:-1]:
            norm_part = {
                "remote": "remotes",
                "role": "roles",
                "partition": "partitions",
            }.get(part, part).replace("-", "_")
            
            if isinstance(obj, dict):
                obj = obj[norm_part]
            elif hasattr(obj, norm_part):
                obj = getattr(obj, norm_part)
            else:
                raise KeyError(f"Option {option_name} not found.")
                
        last_part = parts[-1].replace("-", "_")
        if isinstance(obj, dict):
            if last_part in obj:
                del obj[last_part]
        else:
            setattr(obj, last_part, None)
    else:
        norm_part = option_name.replace("-", "_")
        setattr(config, norm_part, None)


def _list_options(config) -> list:
    options = []
    for field_name, field_value in config:
        if field_name in ("roles", "remotes", "partitions"):
            continue
        if isinstance(field_value, BaseModel):
            for k, v in field_value:
                if v is not None:
                    field_info = field_value.model_fields.get(k)
                    alias = str(field_info.validation_alias) if field_info and field_info.validation_alias else k.replace("_", "-")
                    options.append(f"{field_name}.{alias}: {v}")
                    
    for role_name, role_val in config.roles.items():
        for k, v in role_val:
            if v is not None:
                options.append(f"role.{role_name}.{k}: {v}")
                
    for remote_name, remote_val in config.remotes.items():
        for k, v in remote_val:
            if v is not None:
                options.append(f"remote.{remote_name}.{k}: {v}")
                
    for part_name, part_val in config.partitions.items():
        options.append(f"partition.{part_name}: {part_val}")
        
    return options


@click.group()
def config():
    """Query/update application configuration."""
    pass


@config.command()
@pass_config
@click.argument("option")
def get(config, option):
    """Get the OPTION."""
    click.echo(_get_option(config, option))


@config.command()
@pass_config
@click.argument("option")
@click.argument("value")
def set(config, option, value):
    """Set the OPTION to the given VALUE."""
    _set_option(config, option, value)
    config.save()


@config.command()
@pass_config
@click.argument("option")
def delete(config, option):
    """Delete the OPTION."""
    _delete_option(config, option)
    config.save()
    click.echo("Success.")


@config.command()
@pass_config
def list(config):
    """List all configurations OPTIONS set."""
    r = re.compile(r"(remote\..*\.token: )(.*)")
    for i in _list_options(config):
        m = r.match(i)
        if m:
            i = f"{m[1]}********"
        click.echo(i)


@config.command()
@pass_config
def path(config):
    """Print the location of the user configuration file."""
    click.echo(config.user_config_path)
