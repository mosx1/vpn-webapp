from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from configparser import ConfigParser


class SQLASession:
    
    def __init__(self) -> None:

        config = ConfigParser()
        config.read('config.ini')

        self.engine: Engine = create_engine(
            f"postgresql+psycopg2://{config['Postgres'].get('user')}:{config['Postgres'].get('password')}@{config['Postgres'].get('host')}:{config['Postgres'].get('port')}/{config['Postgres'].get('dbname')}",
            echo=True
        )
        

    def get_session(self) -> Session:
        return sessionmaker(bind=self.engine)()

    def __enter__(self) -> Session:
        self.session: Session = sessionmaker(bind=self.engine)()
        return self.session


    def __exit__(self, type_, value, traceback) -> None:
        self.session.close()