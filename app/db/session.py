from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def create_database_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    connect_args = {}
    engine_options = {}

    if url.get_backend_name() == "sqlite":
        connect_args = {"check_same_thread": False, "timeout": 30}
        if url.database in (None, "", ":memory:"):
            engine_options["poolclass"] = StaticPool
        else:
            database_path = Path(url.database)
            if not database_path.is_absolute() and database_path.parent != Path("."):
                database_path.parent.mkdir(parents=True, exist_ok=True)
        engine_options["connect_args"] = connect_args

    engine = create_engine(database_url, pool_pre_ping=True, **engine_options)

    if url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
