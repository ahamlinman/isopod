from enum import Enum, auto

from sqlalchemy import Engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

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
    status: Mapped[DiscStatus] = mapped_column(default=DiscStatus.RIPPABLE)

    def __repr__(self):
        return f"Disc({self.name}, {self.status})"


def setup(engine: Engine):
    """Initialize the database schema and configure SQLAlchemy sessions to use it."""
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)


def all(session: Session) -> list[Disc]:
    return list(session.scalars(select(Disc)).all())
