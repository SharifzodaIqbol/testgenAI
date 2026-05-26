import logging
import sys
from app.core.config import settings


def setup_logging():
    level = logging.DEBUG if not settings.is_production else logging.INFO
    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Убираем шум от сторонних библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if not settings.is_production else logging.WARNING
    )
