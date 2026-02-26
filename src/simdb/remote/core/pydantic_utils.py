from __future__ import annotations

import contextlib
import copy
import functools
import gzip
import inspect
from typing import (
    Annotated,
    Any,
    get_args,
    get_origin,
)

from flask import Response, request
from flask_restx import Namespace
from pydantic import BaseModel, ValidationError

from simdb.remote.core.errors import error as _error
from simdb.remote.models import ErrorResponse


class ResponseException(Exception):
    """Raised an error has occurred in the request."""

    def __init__(self, message, return_code=400):
        super().__init__(message)
        self.message = message
        self.return_code = return_code


# ---------------------------------------------------------------------------
# Marker classes for Annotated-style parameter declarations
# ---------------------------------------------------------------------------


class _ParamSource:
    """Base class for parameter source markers."""


class Header(_ParamSource):
    """Marker: populate this parameter from ``request.headers``."""


class Body(_ParamSource):
    """Marker: populate this parameter from the JSON request body."""


class Query(_ParamSource):
    """Marker: populate this parameter from ``request.args`` (query string)."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _register_defs(ns: Namespace, defs):
    for name, schema in defs.items():
        # Clean the schema: rewrite refs and remove internal $defs
        clean_schema = copy.deepcopy(schema)
        children = clean_schema.pop("$defs", {})
        ns.schema_model(name, clean_schema)
        _register_defs(ns, children)


def _collect_and_register(ns: Namespace, model: type[BaseModel]):
    """
    Registers a Pydantic model and all nested dependencies to a Flask-RESTX Namespace.
    """
    full_schema = model.model_json_schema(ref_template="#/definitions/{model}")
    all_defs = full_schema.get("$defs", {})

    # 1. Register all sub-models found in $defs first
    _register_defs(ns, all_defs)

    # 2. Register the root model
    root_name = model.__name__
    root_schema = copy.deepcopy(full_schema)
    root_schema.pop("$defs", None)

    return ns.schema_model(root_name, root_schema)


def _get_annotated_params(
    f: Any,
) -> list[tuple[str, type[BaseModel], _ParamSource]]:
    """Inspect *f*'s signature and return a list of ``(param_name, model, source)``
    tuples for every parameter annotated as ``Annotated[SomePydanticModel, Source()]``.
    """
    results = []
    sig = inspect.signature(f)

    for param_name, param in sig.parameters.items():
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            continue
        if get_origin(annotation) is Annotated:
            args = get_args(annotation)
            if len(args) >= 2:
                model_type = args[0]
                source = args[1]
                if (
                    isinstance(source, _ParamSource)
                    and isinstance(model_type, type)
                    and issubclass(model_type, BaseModel)
                ):
                    results.append((param_name, model_type, source))
    return results


def _validate_param(
    model: type[BaseModel],
    source: _ParamSource,
) -> BaseModel:
    """Validate and return a Pydantic model instance from the appropriate
    part of the current Flask request.

    Raises
    ------
    ValidationError
        If the data does not conform to the model.
    ValueError
        If the request body is missing or not valid JSON (for Body sources).
    """
    if isinstance(source, Header):
        # Convert Werkzeug Headers to a plain dict (lowercase keys)
        raw = {k.lower(): v for k, v in request.headers.items()}
        return model.model_validate(raw)

    elif isinstance(source, Query):
        # Convert ImmutableMultiDict to a plain dict (lists for multi-values)
        raw = request.args.to_dict(flat=False)
        # Flatten single-value lists for convenience
        flat = {k: v[0] if len(v) == 1 else v for k, v in raw.items()}
        return model.model_validate(flat)

    else:
        enc = (request.headers.get("Content-Encoding") or "").lower()
        request_data = request.get_data(cache=False)
        if request_data is None:
            raise ValueError("Invalid or missing JSON body")

        if enc == "gzip":
            with contextlib.suppress(OSError):
                request_data = gzip.decompress(request_data)

        return model.model_validate_json(request_data)


# ---------------------------------------------------------------------------
# FastAPI-style route decorator
# ---------------------------------------------------------------------------


def pydantic_validate(
    ns: Namespace,
    *,
    response_model: type[BaseModel] | None = None,
    error_model: type[BaseModel] = ErrorResponse,
    error_codes: tuple[int] = (400,),
) -> Any:
    """Decorator factory that wires up Pydantic validation for a Flask-RESTX endpoint.

    Inspects the decorated function's signature for parameters annotated with
    ``Annotated[SomePydanticModel, Header()]``, ``Annotated[SomePydanticModel, Body()]``
    or ``Annotated[SomePydanticModel, Query()]``, validates the corresponding parts of
    the incoming request, and injects the validated model instances as keyword
    arguments.

    All discovered input models are automatically registered with *ns* for
    Swagger/OpenAPI documentation.  Body models are registered as ``@ns.expect``
    models; header/query models are registered as parser arguments.

    If the function's return annotation is a ``BaseModel`` subclass (or if
    *response_model* is provided explicitly) the return value is automatically
    serialised with ``model_dump(mode="json")`` and wrapped in ``jsonify``.

    Parameters
    ----------
    ns:
        The Flask-RESTX ``Namespace`` (or ``Api``) to register models on.
    response_model:
        Optional explicit response model.  If ``None`` the decorator tries to
        infer it from the function's return annotation.

    Returns
    -------
    A decorator suitable for use on Flask-RESTX ``Resource`` methods.

    Example
    -------
    .. code-block:: python

        from typing import Annotated
        from simdb.remote.core.pydantic_utils import restx_route, Header, Body, Query

        class SimulationList(Resource):
            @restx_route(api)
            def get(
                self,
                user: User,
                pagination: Annotated[PaginationData, Header()],
            ) -> PaginatedResponse:
                ...

            @restx_route(api)
            def post(
                self,
                user: User,
                body: Annotated[SimulationPostData, Body()],
            ) -> SimulationPostResponse:
                ...
    """

    def decorator(f):
        annotated_params = _get_annotated_params(f)

        # Determine response model from return annotation if not given explicitly
        _response_model = response_model
        _error_model = error_model
        if _response_model is None:
            ret = inspect.signature(f).return_annotation
            if (
                ret is not inspect.Parameter.empty
                and inspect.isclass(ret)
                and issubclass(ret, BaseModel)
            ):
                _response_model = ret

        # Register all input models with the namespace
        _registered = {}
        _body_schema = None
        for _param_name, model_type, source in annotated_params:
            schema = _collect_and_register(ns, model_type)
            if isinstance(source, Body):
                _body_schema = schema

        # Register response model
        _resp_schema = None
        if _response_model is not None:
            _resp_schema = _collect_and_register(ns, _response_model)

        _error_schema = None
        if _error_model is not None:
            _error_schema = _collect_and_register(ns, _error_model)

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            for param_name, model_type, source in annotated_params:
                try:
                    validated = _validate_param(model_type, source)
                except ValueError as exc:
                    return _error(str(exc))
                except ValidationError as exc:
                    first_error = exc.errors()[0]
                    loc = " -> ".join(str(loc) for loc in first_error["loc"])
                    msg = f"Validation error at '{loc}': {first_error['msg']}"
                    return _error(msg)
                kwargs[param_name] = validated

            try:
                result = f(*args, **kwargs)
            except ResponseException as err:
                return Response(
                    response=_error_model(error=err.message).model_dump_json(),
                    status=err.return_code,
                    mimetype="application/json",
                )
            except Exception as err:
                return Response(
                    response=_error_model(error=str(err)).model_dump_json(),
                    status=400,  # HTTP status code 500 would make more sense
                    mimetype="application/json",
                )

            if isinstance(result, ErrorResponse):
                return Response(
                    response=result.model_dump_json(),
                    status=400,
                    mimetype="application/json",
                )
            if isinstance(result, BaseModel):
                return Response(
                    result.model_dump_json(),
                    mimetype="application/json",
                )

            return result

        if _body_schema is not None:
            wrapper = ns.expect(_body_schema)(wrapper)
        if _resp_schema is not None:
            wrapper = ns.response(200, "Success", _resp_schema)(wrapper)
        if _error_schema is not None:
            for error_code in error_codes:
                wrapper = ns.response(error_code, "Error", _error_schema)(wrapper)

        return wrapper

    return decorator
