from enum import Enum, auto

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

Session = sessionmaker()


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
