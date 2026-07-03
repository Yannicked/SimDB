import os
import urllib.parse
import warnings
from enum import Enum, auto
from pathlib import Path
from typing import Annotated, Any, Dict, Iterable, List, Literal, Optional, TextIO

import numpy as np
import yaml
from netCDF4 import Dataset
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    UrlConstraints,
    field_validator,
    model_validator,
)

from simdb.imas.utils import SimDBUrl


def _expand_path(path: Path, base_path: Path) -> Path:
    os.environ["MANIFEST_DIR"] = str(base_path)
    path = Path(os.path.expandvars(str(path))).expanduser()
    if not path.is_absolute():
        if not base_path.is_absolute():
            raise ValueError("base_path must be absolute")
        return base_path / path
    else:
        path = path.resolve()
    return path


ManifestUrl = Annotated[SimDBUrl, UrlConstraints(allowed_schemes=["file", "imas"])]


class DataType(Enum):
    UNKNOWN = auto()
    UUID = auto()
    FILE = auto()
    IMAS = auto()


def _get_data_object_type(uri: SimDBUrl) -> "DataType":
    if uri.scheme == "imas":
        return DataType.IMAS
    elif uri.scheme == "file":
        if uri.path is None:
            raise ValueError("no path provided")
        if Path(uri.path).suffix == ".nc":
            with Dataset(uri.path, "r") as ds:
                if getattr(ds, "Conventions", None) == "IMAS":
                    return DataType.IMAS
        return DataType.FILE

    raise ValueError(f"URI scheme ({uri.scheme}:) not recognized")


class DataObject(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    uri: ManifestUrl = Field()

    _type: DataType = PrivateAttr(default=DataType.UNKNOWN)

    @model_validator(mode="after")
    def _resolve_type(self) -> "DataObject":
        self._type = _get_data_object_type(self.uri)
        return self

    @property
    def name(self) -> str:
        return self.uri.encoded_string()

    @field_validator("uri", mode="after")
    @classmethod
    def validate_uri(cls, v: ManifestUrl, info):
        context = info.context or {}
        base_path = context.get("base_path")
        if not base_path:
            base_path = Path.cwd()

        if v.path is None:
            raise ValueError("no uri path provided")

        if v.scheme == "imas":
            qs = dict(v.query_params())
            if "path" not in qs and (
                "shot" not in qs or "run" not in qs or "database" not in qs
            ):
                raise ValueError(
                    "no path or (shot, run, database) provided in IMAS uri"
                )

        elif v.scheme == "file":
            v = v.build(
                scheme="file",
                path=_expand_path(Path(v.path), base_path).as_posix(),
            )

        return v

    @property
    def type(self):
        return self._type


class Source(DataObject):
    pass


class Sink(DataObject):
    pass


def _convert_v1_metadata(metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten version 1 ``values`` metadata entries into version 2 name/value pairs.

    Version 1 stores metadata as a list of ``{"values": {name: value, ...}}``
    entries, whereas version 2 expects a list of single ``{name: value}`` pairs.
    """
    converted: List[Dict[str, Any]] = []
    for entry in metadata:
        values = entry.get("values", {})
        for name, value in values.items():
            converted.append({name: value})
    return converted


class ManifestV1(BaseModel):
    """Manifest schema for version 1.

    Only kept around to load legacy manifests and convert them to the current
    (version 2) format via :meth:`to_v2_data`. Inputs and outputs are carried
    through unchanged (both versions use the ``uri`` form) and are validated by
    :class:`Manifest`; only the metadata layout differs between versions.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    manifest_version: Literal[1] = Field(default=1)
    alias: Optional[str] = None
    responsible_name: Optional[str] = None
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: List[Dict[str, Any]] = Field(default_factory=list)

    def to_v2_data(self) -> Dict[str, Any]:
        """Return the manifest as raw version 2 data ready for ``Manifest``."""
        data: Dict[str, Any] = {
            "manifest_version": 2,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metadata": _convert_v1_metadata(self.metadata),
        }
        if self.alias is not None:
            data["alias"] = self.alias
        if self.responsible_name is not None:
            data["responsible_name"] = self.responsible_name
        return data


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    manifest_version: Literal[2] = Field(default=2)
    alias: Optional[str] = None
    responsible_name: Optional[str] = None
    inputs_raw: List[Source] = Field(default_factory=list, alias="inputs")
    outputs_raw: List[Sink] = Field(default_factory=list, alias="outputs")
    metadata_raw: List[Dict[str, Any]] = Field(default_factory=list, alias="metadata")

    _path: Path = PrivateAttr(default_factory=Path)
    _inputs: List[Source] = PrivateAttr(default_factory=list)
    _outputs: List[Sink] = PrivateAttr(default_factory=list)
    _metadata: Dict[str, Any] = PrivateAttr(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def check_deprecated_version(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        if "version" in data:
            warnings.warn(
                "The 'version' field is deprecated and will be removed "
                "in a future version. Please use 'manifest_version' instead.",
                DeprecationWarning,
                stacklevel=3,
            )
            if "manifest_version" not in data:
                data["manifest_version"] = data.pop("version")

        # Accept legacy version 1 manifests by upgrading them to version 2.
        if data.get("manifest_version") == 1:
            warnings.warn(
                "Manifest version 1 is deprecated and will be removed in a "
                "future version. It has been converted to version 2 in memory; "
                "please update the manifest to version 2.",
                DeprecationWarning,
                stacklevel=3,
            )
            data = ManifestV1.model_validate(data).to_v2_data()

        return data

    @field_validator("alias")
    @classmethod
    def validate_alias(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and urllib.parse.quote(v) != v:
            raise ValueError(f"illegal characters in alias: {v}")
        return v

    @field_validator("metadata_raw")
    @classmethod
    def validate_metadata(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        forbidden_characters = {":", "=", "#"}
        for item in v:
            if len(item) != 1:
                raise ValueError("metadata values should be a name value pair")
            name = next(iter(item))
            bad_chars = set(name).intersection(forbidden_characters)
            if bad_chars:
                raise ValueError(
                    f"invalid metadata field name {name} - "
                    f"contains forbidden character(s): {', '.join(bad_chars)}"
                )
        return v

    @field_validator("inputs_raw", "outputs_raw")
    @classmethod
    def validate_uris(cls, v: List[DataObject], info) -> List[DataObject]:
        seen_uris = set()
        for item in v:
            uri_str = item.name
            if uri_str in seen_uris:
                raise ValueError(
                    "Duplicate URI found in "
                    f"{info.field_name.replace('_raw', '')}: {uri_str}"
                )
            seen_uris.add(uri_str)
        return v

    @model_validator(mode="after")
    def resolve_metadata(self, info) -> "Manifest":
        for metadata_item in self.metadata_raw:
            self._metadata.update(metadata_item)
        return self

    def _resolve_manifest_items(self, items, factory_cls, skip_glob_check):
        resolved = []
        for item in items:
            if item.type == DataType.FILE and item.uri.path:
                path_obj = Path(item.uri.path)

                matches = list(path_obj.parent.glob(path_obj.name))

                if not matches and skip_glob_check:
                    matches = [path_obj]

                if not matches:
                    raise ValueError(f"No files found matching path {path_obj}")

                for p in matches:
                    resolved.append(
                        factory_cls(
                            uri=SimDBUrl.build(scheme="file", path=p.as_posix())
                        )
                    )
            else:
                resolved.append(item)
        return resolved

    @model_validator(mode="after")
    def resolve_inputs_and_outputs(self, info) -> "Manifest":
        context = info.context or {}
        skip_glob_check = context.get("skip_glob_check", False)

        context.setdefault(
            "base_path",
            self._path.absolute().parent if self._path != Path() else Path.cwd(),
        )

        self._inputs = self._resolve_manifest_items(
            self.inputs_raw, Source, skip_glob_check
        )
        self._outputs = self._resolve_manifest_items(
            self.outputs_raw, Sink, skip_glob_check
        )

        return self

    @classmethod
    def _get_loader(cls):
        def ndarray_constructor(
            loader: yaml.SafeLoader, node: yaml.nodes.MappingNode
        ) -> np.ndarray:
            mapping = loader.construct_mapping(node, deep=True)
            return np.array(mapping["data"], mapping.get("dtype", None))

        loader = yaml.SafeLoader
        loader.add_constructor("!ndarray", ndarray_constructor)
        return loader

    @classmethod
    def from_template(cls) -> "Manifest":
        dir_path = Path(__file__).resolve().parent
        with (dir_path / "template.yaml").open() as file:
            try:
                raw_data = yaml.load(file, Loader=cls._get_loader())
            except yaml.YAMLError as err:
                raise ValueError("badly formatted manifest") from err

        model = cls.model_validate(raw_data, context={"skip_glob_check": True})
        model._path = dir_path / "template.yaml"
        return model

    @classmethod
    def load_from_file(
        cls, file_path: Path, overrides: Optional[dict] = None
    ) -> "Manifest":
        with file_path.open() as file:
            try:
                raw_data = yaml.load(file, Loader=cls._get_loader())
            except yaml.YAMLError as err:
                raise ValueError("badly formatted manifest") from err

        if overrides:
            raw_data.update(overrides)

        model = cls.model_validate(
            raw_data, context={"base_path": file_path.absolute().parent}
        )
        model._path = file_path
        return model

    def save(self, out_file: TextIO) -> None:
        yaml.dump(
            self.model_dump(mode="json", by_alias=True, exclude_none=True),
            out_file,
            default_flow_style=False,
        )

    @property
    def version(self) -> int:
        return self.manifest_version

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    @property
    def inputs(self) -> Iterable[Source]:
        return self._inputs

    @property
    def outputs(self) -> Iterable[Sink]:
        return self._outputs
