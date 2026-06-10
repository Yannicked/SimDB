import os
import urllib.parse
from enum import Enum, auto
from pathlib import Path
from typing import Annotated, Any, Dict, Iterable, List, Literal, Optional, TextIO
from uuid import UUID

import numpy as np
import yaml
from netCDF4 import Dataset
from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    UrlConstraints,
    field_validator,
    model_validator,
)


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


ManifestUrl = Annotated[
    AnyUrl, UrlConstraints(allowed_schemes=["file", "imas", "simdb"])
]


class DataType(Enum):
    UNKNOWN = auto()
    UUID = auto()
    FILE = auto()
    IMAS = auto()


def _get_data_object_type(data: dict):
    uri: AnyUrl = data["uri"]

    if uri.scheme == "imas":
        return DataType.IMAS
    elif uri.scheme == "file":
        if uri.path is None:
            raise ValueError("no path provided")
        if Path(uri.path).suffix == ".nc":
            with Dataset(uri.path, "r") as ds:
                if getattr(ds, "Convention", None) == "IMAS":
                    return DataType.IMAS
        return DataType.FILE
    elif uri.scheme == "simdb":
        return DataType.UUID


class DataObject(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    uri: ManifestUrl = Field()

    type: DataType = Field(default_factory=_get_data_object_type)

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
                host="",
                path=_expand_path(Path(v.path), base_path).as_posix(),
            )

        elif v.scheme == "simdb":
            _ = UUID(v.path)

        return v


class Source(DataObject):
    pass


class Sink(DataObject):
    pass


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    manifest_version: Literal[2] = Field(default=2, alias="version")
    alias: Optional[str] = None
    responsible_name: Optional[str] = None
    inputs_raw: List[Source] = Field(default_factory=list, alias="inputs")
    outputs_raw: List[Sink] = Field(default_factory=list, alias="outputs")
    metadata_raw: List[Dict[str, Any]] = Field(default_factory=list, alias="metadata")

    _path: Path = PrivateAttr(default_factory=Path)
    _inputs: List[Source] = PrivateAttr(default_factory=list)
    _outputs: List[Sink] = PrivateAttr(default_factory=list)

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
    def resolve_inputs_and_outputs(self, info) -> "Manifest":
        context = info.context or {}
        skip_glob_check = context.get("skip_glob_check", False)
        base_path = context.get("base_path")
        if not base_path:
            context["base_path"] = (
                self._path.absolute().parent if self._path != Path() else Path.cwd()
            )

        inputs = []
        for i in self.inputs_raw:
            if i.type == DataType.FILE:
                if i.uri.path:
                    source_path = Path(i.uri.path)
                    if not skip_glob_check:
                        names = [
                            p.as_posix()
                            for p in source_path.parent.glob(source_path.name)
                        ]
                        if not names:
                            raise ValueError(
                                f"No files found matching path {source_path}"
                            )
                    else:
                        names = [source_path.as_posix()]
                    for name in names:
                        inputs.append(
                            Source(uri=AnyUrl.build(scheme="file", host="", path=name))
                        )
            else:
                inputs.append(i)
        self._inputs = inputs

        outputs = []
        for i in self.outputs_raw:
            if i.type == DataType.FILE:
                if i.uri.path:
                    sink_path = Path(i.uri.path)
                    names = [
                        p.as_posix() for p in sink_path.parent.glob(sink_path.name)
                    ]
                    if not names and skip_glob_check:
                        names = [sink_path.as_posix()]
                    for name in names:
                        outputs.append(
                            Sink(uri=AnyUrl.build(scheme="file", host="", path=name))
                        )
            else:
                outputs.append(i)
        self._outputs = outputs

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
    def load_from_file(cls, file_path: Path) -> "Manifest":
        with file_path.open() as file:
            try:
                raw_data = yaml.load(file, Loader=cls._get_loader())
            except yaml.YAMLError as err:
                raise ValueError("badly formatted manifest") from err

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
        return {"metadata": self.metadata_raw}

    @property
    def inputs(self) -> Iterable[Source]:
        return self._inputs

    @property
    def outputs(self) -> Iterable[Sink]:
        return self._outputs
