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
)

SessionLocal = sessionmaker(bind=engine)


def create_session() -> Session:
    return SessionLocal()
