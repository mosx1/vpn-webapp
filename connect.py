import logging

from config_loader import read_config
from db.connect import engine

logging.basicConfig(
    level=logging.INFO,
    filename = "logs.txt",
    format="%(asctime)s %(levelname)s %(message)s"
)


config = read_config()
