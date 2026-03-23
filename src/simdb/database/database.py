import contextlib
import sys
import uuid
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Tuple, cast

import appdirs
import sqlalchemy.orm
from sqlalchemy import String, Text, create_engine, exists, func, literal_column, text
from sqlalchemy import cast as sql_cast
from sqlalchemy import or_ as sql_or
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.types import Numeric

from simdb.config import Config
from simdb.query import QueryType

from .models import Base
from .models.file import File
from .models.simulation import Simulation


class DatabaseError(RuntimeError):
    pass


TYPING = TYPE_CHECKING or "sphinx" in sys.modules

if TYPING:
    # Only importing these for type checking and documentation generation in order to
    # speed up runtime startup.
    import sqlalchemy
    from sqlalchemy.orm import scoped_session

    from simdb.query import QueryType

    from .models import Base
    from .models.file import File
    from .models.simulation import Simulation
    from .models.watcher import Watcher

    class Session(scoped_session):
        def query(self, obj: Base, *args, **kwargs) -> Any:
            pass

        def commit(self):
            pass

        def delete(self, obj: Base):
            pass

        def add(self, obj: Base, *args, **kwargs):
            pass

        def rollback(self):
            pass


def _is_hex_string(string: str) -> bool:
    try:
        int(string, 16)
        return True
    except ValueError:
        return False


class Database:
    """
    Class to wrap the database access.
    """

    engine: "sqlalchemy.engine.Engine"
    _session: Optional["sqlalchemy.orm.scoped_session"] = None

    class DBMS(Enum):
        """
        DBMSs supported.
        """

        SQLITE = auto()
        POSTGRESQL = auto()
        MSSQL = auto()

    def __init__(self, db_type: DBMS, scopefunc=None, **kwargs) -> None:
        """
        Create a new Database object.

        :param db_type: The DBMS to use.
        :param kwargs: DBMS specific keyword args:
            SQLITE:
                file: the sqlite database file path
            POSTGRESQL:
                host:       the host to connect to
                port:       the port to connect to
                user:       the user to connect as [optional, defaults to simdb]
                password:   the password for the user [optional, defaults to simdb]
                db_name:    the database name [optional, defaults to simdb]
        """
        if db_type == Database.DBMS.SQLITE:
            if "file" not in kwargs:
                raise ValueError("Missing file parameter for SQLITE database")
            self.engine: sqlalchemy.engine.Engine = create_engine(
                "sqlite:///{file}".format(**kwargs)
            )
            with contextlib.closing(self.engine.connect()) as con:
                res: sqlalchemy.engine.ResultProxy = con.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT "
                    "LIKE 'sqlite_%';"
                )
                new_db = res.rowcount == -1

        elif db_type == Database.DBMS.POSTGRESQL:
            if "host" not in kwargs:
                raise ValueError("Missing host parameter for POSTGRESQL database")
            if "port" not in kwargs:
                raise ValueError("Missing port parameter for POSTGRESQL database")
            kwargs.setdefault("user", "simdb")
            kwargs.setdefault("password", "simdb")
            kwargs.setdefault("db_name", "simdb")

            self.engine: sqlalchemy.engine.Engine = create_engine(
                "postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}".format(
                    **kwargs
                ),
                pool_size=25,
                max_overflow=50,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            with contextlib.closing(self.engine.connect()) as con:
                res: sqlalchemy.engine.ResultProxy = con.execute(
                    "SELECT * FROM pg_catalog.pg_tables WHERE schemaname = 'public';"
                )
                new_db = res.rowcount == 0

        elif db_type == Database.DBMS.MSSQL:
            if "user" not in kwargs:
                raise ValueError("Missing user parameter for MSSQL database")
            if "password" not in kwargs:
                raise ValueError("Missing password parameter for MSSQL database")
            if "dsnname" not in kwargs:
                raise ValueError("Missing dsnname parameter for MSSQL database")
            self.engine: sqlalchemy.engine.Engine = create_engine(
                "mssql+pyodbc://{user}:{password}@{dsnname}".format(**kwargs)
            )
            new_db = False

        else:
            raise ValueError("Unknown database type: " + db_type.name)
        if new_db:
            Base.metadata.create_all(self.engine)
        Base.metadata.bind = self.engine
        if scopefunc is None:

            def scopefunc():
                return 0

        self.session: Session = cast(
            "Session",
            scoped_session(sessionmaker(bind=self.engine), scopefunc=scopefunc),
        )

    def close(self):
        """Close the database session and dispose of the engine."""
        if hasattr(self, "session"):
            self.session.remove()  # For scoped_session
        if hasattr(self, "engine"):
            self.engine.dispose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _json_extract(self, key: str):
        """
        Return a SQLAlchemy column expression that extracts a JSON metadata value
        by key, adapted to the current database dialect.

        For PostgreSQL (JSONB) this uses the ``->`` / ``->>`` operators via
        SQLAlchemy's subscript notation.  For SQLite it uses ``json_extract``.
        The returned expression always yields a *text* value so that string
        comparisons work uniformly across both dialects.
        """
        dialect = self.engine.dialect.name
        if dialect == "postgresql":
            return Simulation._metadata[key].astext
        else:
            return func.json_extract(Simulation._metadata, f"$.{key}")

    def _json_exists(self, key: str):
        """
        Return a SQLAlchemy filter expression that is True when *key* exists in
        the JSON metadata column.
        """
        dialect = self.engine.dialect.name
        if dialect == "postgresql":
            return Simulation._metadata.has_key(key)
        else:
            return func.json_type(Simulation._metadata, f"$.{key}").isnot(None)

    def _apply_json_filter(self, query, name: str, value: str, query_type: "QueryType"):
        """
        Append a WHERE clause to *query* that filters on a JSON metadata key
        using the database's native JSON operators.

        Numeric comparisons (GT / GE / LT / LE) cast the extracted text to a
        NUMERIC type so that ``"10" > "9"`` evaluates correctly.

        :param query: The current SQLAlchemy query.
        :param name: The metadata key to filter on.
        :param value: The value to compare against (always a string from the URL).
        :param query_type: The comparison operator.
        :return: The updated query.
        """
        col_text = self._json_extract(name)

        if query_type == QueryType.EXIST:
            return query.filter(self._json_exists(name))

        if query_type == QueryType.EQ:
            return query.filter(func.lower(col_text) == value.lower())

        if query_type == QueryType.NE:
            return query.filter(func.lower(col_text) != value.lower())

        if query_type == QueryType.IN:
            return query.filter(func.lower(col_text).contains(value.lower()))

        if query_type == QueryType.NI:
            return query.filter(
                sql_or(
                    col_text.is_(None),
                    ~func.lower(col_text).contains(value.lower()),
                )
            )

        col_num = sql_cast(col_text, Numeric)
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            # Fall back to text comparison when the value is not numeric
            col_num = col_text
            num_value = value

        if query_type == QueryType.GT:
            return query.filter(col_num > num_value)
        if query_type == QueryType.GE:
            return query.filter(col_num >= num_value)
        if query_type == QueryType.LT:
            return query.filter(col_num < num_value)
        if query_type == QueryType.LE:
            return query.filter(col_num <= num_value)

        # AGT / AGE / ALT / ALE: "any element of the array satisfies the comparison"
        # Use an EXISTS subquery that unnests the JSON array and compares each element.
        if query_type in (QueryType.AGT, QueryType.AGE, QueryType.ALT, QueryType.ALE):
            return query.filter(self._any_array_element_filter(name, num_value, query_type))

        return query

    def _any_array_element_filter(self, name: str, num_value, query_type: "QueryType"):
        """
        Return an EXISTS clause that is True when *any* element of the JSON array
        stored at metadata key *name* satisfies the numeric comparison *query_type*.

        For PostgreSQL the subquery uses ``jsonb_array_elements_text``.
        For SQLite the subquery uses ``json_each``.

        :param name: The metadata key whose value is a JSON array.
        :param num_value: The numeric threshold to compare against.
        :param query_type: One of AGT / AGE / ALT / ALE.
        :return: A SQLAlchemy clause element suitable for use in ``.filter()``.
        """
        dialect = self.engine.dialect.name

        ops = {
            QueryType.AGT: ">",
            QueryType.AGE: ">=",
            QueryType.ALT: "<",
            QueryType.ALE: "<=",
        }
        op = ops[query_type]

        if dialect == "postgresql":
            raw = text(
                f"EXISTS ("
                f"  SELECT 1"
                f"  FROM jsonb_array_elements_text(simulations.metadata -> :key) AS elem"
                f"  WHERE CAST(elem AS NUMERIC) {op} :val"
                f")"
            ).bindparams(key=name, val=num_value)
        else:
            raw = text(
                f"EXISTS ("
                f"  SELECT 1"
                f"  FROM json_each(simulations.metadata, '$.' || :key) AS je"
                f"  WHERE CAST(je.value AS REAL) {op} :val"
                f")"
            ).bindparams(key=name, val=num_value)

        return raw

    def _apply_sort(self, query, sort_by: str, sort_asc: bool):
        """
        Append an ORDER BY clause to *query*.

        Sorting on ``alias``, ``uuid`` and ``datetime`` uses the corresponding
        ORM columns directly.  Sorting on any other field extracts the value
        from the JSON metadata column using the dialect-appropriate expression.

        NULL values are always sorted last regardless of direction.
        """
        if not sort_by:
            return query

        dialect = self.engine.dialect.name

        if sort_by == "alias":
            col = Simulation.alias
        elif sort_by == "uuid":
            col = sql_cast(Simulation.uuid, String)
        elif sort_by == "datetime":
            col = Simulation.datetime
        else:
            col = self._json_extract(sort_by)

        if sort_asc:
            if dialect == "postgresql":
                from sqlalchemy import asc, nulls_last

                order_expr = nulls_last(asc(col))
            else:
                order_expr = col.asc()
        else:
            if dialect == "postgresql":
                from sqlalchemy import desc, nulls_last

                order_expr = nulls_last(desc(col))
            else:
                order_expr = col.desc()

        return query.order_by(order_expr)

    def _get_simulation_data(
        self, query, meta_keys, limit, page, sort_by="", sort_asc=False
    ) -> Tuple[int, List]:
        """
        Build simulation data from query results with JSON metadata.

        Sorting is pushed to the database via :meth:`_apply_sort`.  Pagination
        is also performed at the database level when a *limit* is given.

        :param query: SQLAlchemy query object
        :param meta_keys: List of metadata keys to include
        :param limit: Maximum number of results per page
        :param page: Page number (1-indexed)
        :param sort_by: Field name to sort by (can be alias/uuid/datetime/metadata key)
        :param sort_asc: Sort in ascending order if True, descending if False
        :return: Tuple of (total_count, list of simulation dicts)
        """
        # Apply DB-level sorting before counting / paginating
        query = self._apply_sort(query, sort_by, sort_asc)

        total_count = query.count()

        if limit:
            offset = (page - 1) * limit
            query = query.limit(limit).offset(offset)

        results = []
        for row in query.all():
            sim_data = {
                "alias": row.alias,
                "uuid": row.uuid,
                "datetime": row.datetime.isoformat(),
            }

            meta_dict = row._metadata or {}

            if meta_keys:
                sim_data["metadata"] = [
                    {"element": k, "value": v}
                    for k, v in meta_dict.items()
                    if k in meta_keys
                ]

            results.append(sim_data)

        return total_count, results

    def _find_simulation(self, sim_ref: str) -> "Simulation":
        try:
            sim_uuid = uuid.UUID(sim_ref)
            simulation = (
                self.session.query(Simulation).filter_by(uuid=sim_uuid).one_or_none()
            )
        except ValueError:
            try:
                simulation = (
                    self.session.query(Simulation)
                    .filter(
                        sql_or(
                            sql_cast(Simulation.uuid, Text).startswith(sim_ref),
                            Simulation.alias == sim_ref,
                        )
                    )
                    .one_or_none()
                )
            except SQLAlchemyError:
                simulation = None
            if not simulation:
                raise DatabaseError(f"Simulation {sim_ref} not found.") from None
        return simulation

    def remove(self):
        """
        Remove the current session
        """
        if self.session:
            self.session.remove()

    def reset(self) -> None:
        """
        Clear all the data out of the database.

        :return: None
        """

        with contextlib.closing(self.engine.connect()) as con:
            trans = con.begin()
            for table in reversed(Base.metadata.sorted_tables):
                con.execute(table.delete())
            trans.commit()

    def list_simulations(
        self, meta_keys: Optional[List[str]] = None, limit: int = 0
    ) -> List["Simulation"]:
        """
        Return a list of all the simulations stored in the database.

        :return: A list of Simulations.
        """
        query = self.session.query(Simulation)
        if limit:
            query = query.limit(limit)
        return query.all()

    def list_simulation_data(
        self,
        meta_keys: Optional[List[str]] = None,
        limit: int = 0,
        page: int = 1,
        sort_by: str = "",
        sort_asc: bool = False,
    ) -> Tuple[int, List[dict]]:
        """
        Return a list of all the simulations stored in the database.

        :return: A tuple of (total_count, list of simulation data dicts).
        """
        query = self.session.query(Simulation)

        return self._get_simulation_data(
            query, meta_keys, limit, page, sort_by, sort_asc
        )

    def get_simulation_data(self, query):
        limit_query = query
        return limit_query

    def list_files(self) -> List["File"]:
        """
        Return a list of all the files stored in the database.

        :return:  A list of Files.
        """

        return self.session.query(File).all()

    def delete_simulation(self, sim_ref: str) -> "Simulation":
        """
        Delete the specified simulation from the database.

        :param sim_ref: The simulation UUID or alias.
        :return: None
        """
        simulation = self._find_simulation(sim_ref)
        for file in simulation.inputs:
            self.session.delete(file)
        for file in simulation.outputs:
            self.session.delete(file)
        self.session.delete(simulation)
        self.session.commit()
        return simulation

    def _build_constrained_query(self, base_query, constraints: List[Tuple[str, str, "QueryType"]]):
        """
        Apply all *constraints* as WHERE clauses to *base_query* and return the
        updated query.

        Filtering is performed entirely at the database level using SQLAlchemy's
        JSON column operators so that no full table scan in Python is required.
        Each constraint is translated to a WHERE clause via
        :meth:`_apply_json_filter` for metadata keys, or via direct ORM column
        comparisons for the special fields ``alias``, ``uuid`` and
        ``creation_date``.

        :param base_query: A SQLAlchemy query to add filters to.
        :param constraints: List of ``(name, value, query_type)`` tuples.
        :return: The updated query with all filters applied.
        """
        for name, value, query_type in constraints:
            if name == "alias":
                if query_type == QueryType.EQ:
                    base_query = base_query.filter(
                        func.lower(Simulation.alias) == value.lower()
                    )
                elif query_type == QueryType.IN:
                    base_query = base_query.filter(
                        Simulation.alias.ilike(f"%{value}%")
                    )
                elif query_type == QueryType.NI:
                    base_query = base_query.filter(
                        Simulation.alias.notilike(f"%{value}%")
                    )
                elif query_type == QueryType.NE:
                    base_query = base_query.filter(
                        func.lower(Simulation.alias) != value.lower()
                    )
            elif name == "uuid":
                if query_type == QueryType.EQ:
                    base_query = base_query.filter(
                        Simulation.uuid == uuid.UUID(value)
                    )
                elif query_type == QueryType.IN:
                    base_query = base_query.filter(
                        func.REPLACE(
                            sql_cast(Simulation.uuid, String), "-", ""
                        ).ilike("%{}%".format(value.replace("-", "")))
                    )
                elif query_type == QueryType.NI:
                    base_query = base_query.filter(
                        func.REPLACE(
                            sql_cast(Simulation.uuid, String), "-", ""
                        ).notilike("%{}%".format(value.replace("-", "")))
                    )
                elif query_type == QueryType.NE:
                    base_query = base_query.filter(
                        Simulation.uuid != uuid.UUID(value)
                    )
            elif name == "creation_date":
                date_time = datetime.strptime(
                    value.replace("_", ":"), "%Y-%m-%d %H:%M:%S"
                )
                if query_type == QueryType.EQ:
                    base_query = base_query.filter(Simulation.datetime == date_time)
                elif query_type == QueryType.GT:
                    base_query = base_query.filter(Simulation.datetime > date_time)
                elif query_type == QueryType.GE:
                    base_query = base_query.filter(Simulation.datetime >= date_time)
                elif query_type == QueryType.LT:
                    base_query = base_query.filter(Simulation.datetime < date_time)
                elif query_type == QueryType.LE:
                    base_query = base_query.filter(Simulation.datetime <= date_time)
                elif query_type == QueryType.NE:
                    base_query = base_query.filter(Simulation.datetime != date_time)
            else:
                # JSON metadata field - push the filter to the database
                base_query = self._apply_json_filter(base_query, name, value, query_type)

        return base_query

    def query_meta(
        self, constraints: List[Tuple[str, str, "QueryType"]]
    ) -> List["Simulation"]:
        """
        Query the metadata and return matching simulations.

        All filtering is performed at the database level via
        :meth:`_build_constrained_query`.

        :return: List of matching :class:`Simulation` objects.
        """
        query = self._build_constrained_query(
            self.session.query(Simulation), constraints
        )
        return query.all()

    def query_meta_data(
        self,
        constraints: List[Tuple[str, str, "QueryType"]],
        meta_keys: List[str],
        limit: int = 0,
        page: int = 1,
        sort_by: str = "",
        sort_asc: bool = False,
    ) -> Tuple[int, List[dict]]:
        """
        Query the metadata and return matching simulations as plain dicts.

        All filtering is performed at the database level via
        :meth:`_build_constrained_query`.  Sorting and pagination are also
        pushed to the database inside :meth:`_get_simulation_data`.

        :return: Tuple of ``(total_count, list of simulation data dicts)``.
        """
        query = self._build_constrained_query(
            self.session.query(Simulation), constraints
        )
        return self._get_simulation_data(
            query, meta_keys, limit, page, sort_by, sort_asc
        )

    def get_simulation(self, sim_ref: str) -> "Simulation":
        """
        Get the specified simulation from the database.

        :param sim_ref: The simulation UUID or alias.
        :return: The Simulation.
        """
        simulation = self._find_simulation(sim_ref)
        return simulation

    def get_simulation_parents(self, simulation: "Simulation") -> List[dict]:
        subquery = (
            self.session.query(File.checksum)
            .filter(File.checksum != "")
            .filter(File.input_for.contains(simulation))
            .subquery()
        )
        query = (
            self.session.query(Simulation.uuid, Simulation.alias)
            .join(Simulation.outputs)
            .filter(File.checksum.in_(subquery))
            .filter(Simulation.alias != simulation.alias)
            .distinct()
        )
        return [{"uuid": r.uuid, "alias": r.alias} for r in query.all()]

    def get_simulation_children(self, simulation: "Simulation") -> List[dict]:
        subquery = (
            self.session.query(File.checksum)
            .filter(File.checksum != "")
            .filter(File.output_of.contains(simulation))
            .subquery()
        )
        query = (
            self.session.query(Simulation.uuid, Simulation.alias)
            .join(Simulation.inputs)
            .filter(File.checksum.in_(subquery))
            .filter(Simulation.alias != simulation.alias)
            .distinct()
        )
        return [{"uuid": r.uuid, "alias": r.alias} for r in query.all()]

    def get_file(self, file_uuid_str: str) -> "File":
        """
        Get the specified file from the database.

        :param file_uuid_str: The string representation of the file UUID.
        :return: The File.
        """

        try:
            file_uuid = uuid.UUID(file_uuid_str)
            file = self.session.query(File).filter_by(uuid=file_uuid).one_or_none()
        except ValueError as err:
            raise DatabaseError(f"Invalid UUID {file_uuid_str}.") from err
        if file is None:
            raise DatabaseError(f"Failed to find file {file_uuid.hex}.")
        self.session.commit()
        return file

    def get_metadata(self, sim_ref: str, name: str) -> List[str]:
        """
        Get all the metadata for the given simulation with the given key.

        :param sim_ref: the simulation identifier
        :param name: the metadata key
        :return: The matching metadata values.
        """
        simulation = self._find_simulation(sim_ref)
        self.session.commit()
        return simulation.find_meta(name)

    def add_watcher(self, sim_ref: str, watcher: "Watcher"):
        sim = self._find_simulation(sim_ref)
        sim.watchers.append(watcher)
        self.session.commit()

    def remove_watcher(self, sim_ref: str, username: str):
        sim = self._find_simulation(sim_ref)
        watchers = [w for w in sim.watchers if w.username == username]
        if not watchers:
            raise DatabaseError(f"Watcher not found for simulation {sim_ref}.")
        for watcher in watchers:
            sim.watchers.remove(watcher)
        self.session.commit()

    def list_watchers(self, sim_ref: str) -> List["Watcher"]:
        return self._find_simulation(sim_ref).watchers

    def list_metadata_keys(self) -> List[dict]:
        simulations = self.session.query(Simulation._metadata).all()

        keys_dict = {}
        for (meta_dict,) in simulations:
            if meta_dict:
                for key, value in meta_dict.items():
                    if key not in keys_dict:
                        keys_dict[key] = value

        return [{"name": k, "type": type(v).__name__} for k, v in keys_dict.items()]

    def list_metadata_values(self, name: str) -> List[str]:
        if name == "alias":
            query = self.session.query(Simulation.alias).filter(
                Simulation.alias.isnot(None)
            )
            data = [row[0] for row in query.all()]
        else:
            # Extract the specific key from the JSON column at the database level
            col = self._json_extract(name)
            query = (
                self.session.query(col.label("val"))
                .filter(self._json_exists(name))
                .distinct()
            )
            data = [str(row.val) for row in query.all() if row.val is not None]

        try:
            return sorted(data)
        except TypeError:
            return data

    def insert_simulation(self, simulation: "Simulation") -> None:
        """
        Insert the given simulation into the database.

        :param simulation: The Simulation to insert.
        :return: None
        """

        try:
            self.session.add(simulation)
            self.session.commit()
        except IntegrityError as err:
            self.session.rollback()
            if "alias" in str(err.orig):
                raise DatabaseError(
                    f"Simulation already exists with alias {simulation.alias} - please "
                    "use a unique alias."
                ) from err
            elif "uuid" in str(err.orig):
                raise DatabaseError(
                    f"Simulation already exists with uuid {simulation.uuid}."
                ) from err
            raise DatabaseError(str(err.orig)) from err
        except DBAPIError as err:
            self.session.rollback()
            raise DatabaseError(str(err.orig)) from err

    def get_aliases(self, prefix: Optional[str]) -> List[str]:
        if prefix:
            query = self.session.query(Simulation.alias).filter(
                Simulation.alias.ilike(prefix + "%")
            )
            return [alias for (alias,) in query.all()]
        else:
            query = self.session.query(Simulation.alias)
            return [alias for (alias,) in query.all()]


def get_local_db(config: Config) -> Database:
    db_file = Path(
        config.get_string_option("db.file", default=None)
        or f"{appdirs.user_data_dir('simdb')}/sim.db"
    )
    db_file.parent.mkdir(parents=True, exist_ok=True)
    database = Database(Database.DBMS.SQLITE, file=db_file)
    return database
