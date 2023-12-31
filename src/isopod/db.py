import logging
from enum import Enum, auto

from pyudev import Device
from sqlalchemy import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

import isopod.linux

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


class LastRip(Base):
    __tablename__ = "lastrip"

    bootid: Mapped[str] = mapped_column(primary_key=True)
    devpath: Mapped[str] = mapped_column(primary_key=True)
    diskseq: Mapped[str] = mapped_column(primary_key=True)

    @classmethod
    def for_device(_cls, dev: str | Device):
        dev = isopod.linux.get_device(dev) if isinstance(dev, str) else dev
        bootid = isopod.linux.get_boot_id()
        diskseq = isopod.linux.get_diskseq(dev)
        return LastRip(bootid=bootid, devpath=dev.device_path, diskseq=diskseq)
