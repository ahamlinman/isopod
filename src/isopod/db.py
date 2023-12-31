import logging
from enum import Enum, auto

from sqlalchemy import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

log = logging.getLogger(__name__)

Session = sessionmaker()


class Base(DeclarativeBase):
    pass


def setup(engine: Engine):
    """Initialize the database schema and configure SQLAlchemy sessions to use it."""
    log.info("Configuring database: %s", engine)
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)


class DiscStatus(Enum):
    RIPPABLE = auto()
    SENDABLE = auto()
    COMPLETE = auto()


class Disc(Base):
    __tablename__ = "isopod_discs"

    path: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[DiscStatus] = mapped_column(default=DiscStatus.RIPPABLE)
    # TODO: Consider tracking boot ID and diskseq.

    def __repr__(self):
        return f"Disc({self.name}, {self.status})"
