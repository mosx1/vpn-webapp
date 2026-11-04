import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from config_loader import read_config

_config = read_config()

engine: Engine = create_engine(
    (
        f"postgresql+psycopg2://{_config['Postgres'].get('user')}:"
        f"{_config['Postgres'].get('password')}@{_config['Postgres'].get('host')}:"
        f"{_config['Postgres'].get('port')}/{_config['Postgres'].get('dbname')}"
    ),
    echo=_config['Postgres'].getboolean('echo', False),
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "8")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "16")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
)

SessionLocal = sessionmaker(bind=engine)


def create_session() -> Session:
    return SessionLocal()
