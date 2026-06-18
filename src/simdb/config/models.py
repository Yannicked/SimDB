"""Pydantic models for SimDB configuration settings."""

import configparser
from pathlib import Path
from typing import Annotated, Any, Dict, Literal, Optional, Union

import appdirs
from pydantic import BaseModel, ConfigDict, Field

CONFIG_FILE_NAME: str = "simdb.cfg"


class FlaskSettings(BaseModel):
    """Flask framework settings."""

    model_config = ConfigDict()

    flask_env: str = Field(default="production", validation_alias="flask_env")
    debug: bool = Field(default=False)
    testing: bool = Field(default=False)
    secret_key: str = Field(default="CHANGE_ME", validation_alias="secret_key")


class ServerSettings(BaseModel):
    """SimDB remote server settings."""

    model_config = ConfigDict()

    upload_folder: Path = Field(
        default=Path("/tmp/simdb/simulations"), validation_alias="upload_folder"
    )
    user_upload_folder: Optional[str] = Field(
        default=None, validation_alias="user_upload_folder"
    )
    ssl_enabled: bool = Field(default=False, validation_alias="ssl_enabled")
    ssl_cert_file: Optional[str] = Field(default=None, validation_alias="ssl_cert_file")
    ssl_key_file: Optional[str] = Field(default=None, validation_alias="ssl_key_file")
    admin_password: Optional[str] = Field(
        default=None, validation_alias="admin_password"
    )
    copy_files: bool = Field(default=True, validation_alias="copy_files")
    copy_ids: bool = Field(default=True, validation_alias="copy_ids")
    imas_remote_host: Optional[str] = Field(
        default=None, validation_alias="imas_remote_host"
    )
    imas_remote_port: Optional[int] = Field(
        default=None, validation_alias="imas_remote_port"
    )
    token_lifetime: int = Field(default=30, validation_alias="token_lifetime")


class PostgresDatabaseSettings(BaseModel):
    model_config = ConfigDict()

    type: Literal["postgres"] = Field(default="postgres")
    host: str = Field()
    port: str = Field()
    user: str = Field(default="simdb")
    password: str = Field(default="simdb")
    db_name: str = Field(default="simdb")


class SQLiteDatabaseSettings(BaseModel):
    model_config = ConfigDict()

    type: Literal["sqlite"] = Field(default="sqlite")
    file: Path = Field(
        default_factory=lambda: Path(appdirs.user_data_dir("simdb")) / "sim.db"
    )


DatabaseSettings = Annotated[
    Union[PostgresDatabaseSettings, SQLiteDatabaseSettings], Field(discriminator="type")
]


class ClientDbSettings(BaseModel):
    """Database settings for the SimDB client."""

    model_config = ConfigDict()

    type: str = Field(default="sqlite")
    file: Optional[str] = Field(default=None)


class ValidationSettings(BaseModel):
    """Simulation data validation settings."""

    model_config = ConfigDict(extra="allow")

    auto_validate: bool = Field(default=True, validation_alias="auto_validate")
    error_on_fail: bool = Field(default=True, validation_alias="error_on_fail")
    file_validator_type: Optional[str] = Field(
        default=None, validation_alias="file_validator_type"
    )
    path: Optional[Path] = Field(default=None)


class EmailSettings(BaseModel):
    """Email notification server settings."""

    model_config = ConfigDict()

    server: Optional[str] = Field(default=None)
    port: Optional[int] = Field(default=None)
    user: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)


class DevelopmentSettings(BaseModel):
    """Development and debugging settings."""

    model_config = ConfigDict()

    disable_checksum: bool = Field(default=False, validation_alias="disable_checksum")
    disable_replaces: bool = Field(default=False, validation_alias="disable_replaces")


class AuthenticationSettings(BaseModel):
    """User authentication settings (LDAP, AD, Keycloak, etc.)."""

    model_config = ConfigDict()

    type: Optional[str] = Field(default=None)
    ldap_server: Optional[str] = Field(default=None, validation_alias="ldap_server")
    ldap_bind: Optional[str] = Field(default=None, validation_alias="ldap_bind")
    ldap_query_user: Optional[str] = Field(
        default=None, validation_alias="ldap_query_user"
    )
    ldap_query_password: Optional[str] = Field(
        default=None, validation_alias="ldap_query_password"
    )
    ldap_query_base: Optional[str] = Field(
        default=None, validation_alias="ldap_query_base"
    )
    ldap_query_filter: Optional[str] = Field(
        default=None, validation_alias="ldap_query_filter"
    )
    ldap_query_uid: str = Field(default="uid", validation_alias="ldap_query_uid")
    ldap_query_mail: str = Field(default="mail", validation_alias="ldap_query_mail")
    server_url: Optional[str] = Field(default=None, validation_alias="server_url")
    realm_name: Optional[str] = Field(default=None, validation_alias="realm_name")
    client_id: Optional[str] = Field(default=None, validation_alias="client_id")
    ad_server: Optional[str] = Field(default=None, validation_alias="ad_server")
    ad_domain: Optional[str] = Field(default=None, validation_alias="ad_domain")
    ad_cert: Optional[str] = Field(default=None, validation_alias="ad_cert")
    firewall_user: Optional[str] = Field(default=None, validation_alias="firewall_user")
    firewall_email: Optional[str] = Field(
        default=None, validation_alias="firewall_email"
    )


class UserSettings(BaseModel):
    """User profile settings."""

    model_config = ConfigDict()

    name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    config_path: Path = Field(
        default_factory=lambda: (
            Path(appdirs.user_config_dir("simdb")) / CONFIG_FILE_NAME
        ),
        validation_alias="config-path",
    )


class SiteSettings(BaseModel):
    """Site-wide overrides or paths."""

    model_config = ConfigDict()

    config_path: Path = Field(
        default_factory=lambda: (
            Path(appdirs.site_config_dir("simdb")) / CONFIG_FILE_NAME
        ),
        validation_alias="config-path",
    )


class RoleSettings(BaseModel):
    """Configuration of user roles."""

    model_config = ConfigDict()

    users: str = Field(default="")


class RemoteSettings(BaseModel):
    """Remote API server connection settings."""

    model_config = ConfigDict()

    url: str
    default: bool = Field(default=False)
    username: str = Field(default="")
    token: str = Field(default="")
    firewall: Optional[str] = Field(default=None)


def _normalize_config_to_dict(data: Any) -> Dict[str, Any]:
    """
    Normalizes any input (Dict, ConfigParser) into a standard
    nested dictionary structure that matches your model.
    """
    if isinstance(data, dict):
        return data  # Assume dicts are already structured

    if isinstance(data, (configparser.ConfigParser, getattr(data, "_parser", None))):
        parser = data if isinstance(data, configparser.ConfigParser) else data._parser
        result = {}
        for section in parser.sections():
            parts = section.split(" ")
            main_key = {
                "role": "roles",
                "remote": "remotes",
                "partition": "partitions",
            }.get(parts[0], parts[0])

            # Extract section values
            section_data = {
                opt: parser.get(section, opt) for opt in parser.options(section)
            }

            if len(parts) > 1:
                sub_key = parts[1].strip('"')
                result.setdefault(main_key, {})[sub_key] = section_data
            else:
                result[main_key] = section_data
        return result

    return {}


class ConfigError(Exception):
    pass


class SimDBSettings(BaseModel):
    """Root configuration model containing all SimDB settings."""

    model_config = ConfigDict(extra="allow")

    flask: FlaskSettings = Field(default_factory=FlaskSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    database: DatabaseSettings = Field(default=SQLiteDatabaseSettings())
    validation: ValidationSettings = Field(default_factory=ValidationSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    development: DevelopmentSettings = Field(default_factory=DevelopmentSettings)
    authentication: AuthenticationSettings = Field(
        default_factory=AuthenticationSettings
    )
    user: UserSettings = Field(default_factory=UserSettings)
    site: SiteSettings = Field(default_factory=SiteSettings)
    roles: Dict[str, RoleSettings] = Field(default_factory=dict)
    remotes: Dict[str, RemoteSettings] = Field(default_factory=dict)
    partitions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    @property
    def default_remote(self) -> Optional[str]:
        for name, remote in self.remotes.items():
            if remote.default:
                return name
        return None

    @default_remote.setter
    def default_remote(self, value: str) -> None:
        for name, remote in self.remotes.items():
            remote.default = (name == value)

    @property
    def api_version(self) -> str:
        return "1.2"

    def save(self) -> None:
        import os
        parser = configparser.ConfigParser()
        
        for field_name, field_value in self:
            if field_name in ("roles", "remotes", "partitions"):
                continue
            if isinstance(field_value, BaseModel):
                section_name = field_name
                if not parser.has_section(section_name):
                    parser.add_section(section_name)
                for k, v in field_value:
                    if v is not None:
                        field_info = field_value.model_fields.get(k)
                        alias = str(field_info.validation_alias) if field_info and field_info.validation_alias else k.replace("_", "-")
                        parser.set(section_name, alias, str(v))
                        
        for role_name, role_val in self.roles.items():
            section_name = f'role "{role_name}"'
            if not parser.has_section(section_name):
                parser.add_section(section_name)
            for k, v in role_val:
                if v is not None:
                    parser.set(section_name, k, str(v))
                    
        for remote_name, remote_val in self.remotes.items():
            section_name = f'remote "{remote_name}"'
            if not parser.has_section(section_name):
                parser.add_section(section_name)
            for k, v in remote_val:
                if v is not None:
                    field_info = remote_val.model_fields.get(k)
                    alias = str(field_info.validation_alias) if field_info and field_info.validation_alias else k.replace("_", "-")
                    parser.set(section_name, alias, str(v).lower() if isinstance(v, bool) else str(v))
                    
        for part_name, part_val in self.partitions.items():
            section_name = f'partition "{part_name}"'
            if not parser.has_section(section_name):
                parser.add_section(section_name)
            parser.set(section_name, "value", str(part_val))
            
        user_config_path = self.user.config_path
        user_config_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(
            user_config_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
        )
        with os.fdopen(fd, "w") as file:
            parser.write(file)

    @staticmethod
    def load(file_path: Optional[Any] = None) -> "SimDBSettings":
        config = configparser.ConfigParser()

        user_config_path = UserSettings().config_path
        site_config_path = SiteSettings().config_path
        config.read((user_config_path, site_config_path))

        if file_path is not None:
            if hasattr(file_path, "read"):
                config.read_file(file_path)
            else:
                config.read(file_path)

        settings = SimDBSettings.from_config(config)

        if file_path is not None:
            if hasattr(file_path, "read"):
                if hasattr(file_path, "name") and file_path.name:
                    settings.user.config_path = Path(file_path.name).absolute()
            else:
                settings.user.config_path = Path(file_path).absolute()

        return settings

    @classmethod
    def from_config(cls, data: Any) -> "SimDBSettings":
        if isinstance(data, cls):
            return data

        # Normalize to dict and instantiate
        normalized_data = _normalize_config_to_dict(data)
        return cls.model_validate(normalized_data)
