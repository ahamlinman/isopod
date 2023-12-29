import logging
from dataclasses import dataclass
from enum import Enum, auto

from sqlalchemy import Column, MetaData, String, Table, create_engine, text
from sqlalchemy.orm import Session

# Work around SQLAlchemy adding their own handler for echo=True, even though we
# already have one at the root.
logging.getLogger("sqlalchemy.engine.Engine").addHandler(logging.NullHandler())

metadata_obj = MetaData()

discs_table = Table(
    "isopod_discs",
    metadata_obj,
    Column("name", String, primary_key=True),
    Column("status", String),
)


class DiscStatus(Enum):
    RIPPABLE = auto()
    SENDABLE = auto()
    COMPLETE = auto()


@dataclass
class Disc:
    name: str
    status: DiscStatus


class Registry:
    def __init__(self, db_path: str):
        # TODO: Remove echo=True after initial debugging.
        self._engine = create_engine(f"sqlite+pysqlite:///{db_path}", echo=True)
        metadata_obj.create_all(self._engine)
