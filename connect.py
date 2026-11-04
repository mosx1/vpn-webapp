import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config_loader import read_config
from db.connect import engine

_LOG_FILE_PATH = Path(__file__).resolve().parent / "logs.txt"
_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

_file_handler = RotatingFileHandler(
    _LOG_FILE_PATH,
    maxBytes=10 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(_formatter)

_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[_file_handler, _stream_handler],
    force=True,
)


config = read_config()
