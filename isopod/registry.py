import logging
from enum import Enum, auto

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# Work around SQLAlchemy adding their own handler for echo=True, even though we
# already have one at the root.
logging.getLogger("sqlalchemy.engine.Engine").addHandler(logging.NullHandler())


class Base(DeclarativeBase):
    pass


class DiscStatus(Enum):
    RIPPABLE = auto()
    SENDABLE = auto()
    COMPLETE = auto()


class Disc(Base):
    __tablename__ = "isopod_discs"

    name: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[DiscStatus]


class Registry:
    def __init__(self, db_path: str):
        # TODO: Remove echo=True after initial debugging.
        self._engine = create_engine(f"sqlite+pysqlite:///{db_path}", echo=True)
        Base.metadata.create_all(self._engine)

    def put(self, disc: Disc):
        with Session(self._engine) as session:
            session.merge(disc)
            session.flush()
            session.commit()
