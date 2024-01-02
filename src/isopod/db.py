import datetime
import logging
from enum import Enum, auto
from typing import Optional

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
    __tablename__ = "discs"

    path: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[DiscStatus] = mapped_column(default=DiscStatus.RIPPABLE)
    source_hash: Mapped[Optional[bytes]]
    send_attempts: Mapped[int] = mapped_column(default=0)
    last_send_failure: Mapped[Optional[datetime.datetime]]
