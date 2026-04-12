import logging

from sqlalchemy import Engine, create_engine

from config_loader import read_config

logging.basicConfig(
    level=logging.INFO,
    filename = "logs.txt",
    format="%(asctime)s %(levelname)s %(message)s"
)


config = read_config()

engine: Engine = create_engine(
    f"postgresql+psycopg2://{config['Postgres'].get('user')}:{config['Postgres'].get('password')}@{config['Postgres'].get('host')}:{config['Postgres'].get('port')}/{config['Postgres'].get('dbname')}"
)