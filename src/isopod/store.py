from enum import Enum, auto

from sqlalchemy import Engine, select
from sqlalchemy.exc import NoResultFound
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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    status: Mapped[DiscStatus] = mapped_column(default=DiscStatus.RIPPABLE)
    # TODO: Remove default for src_device.
    src_device: Mapped[str] = mapped_column(default="/dev/cdrom")

    def __repr__(self):
        return f"Disc({self.name}, {self.status})"


def setup(engine: Engine):
    """Initialize the database schema and configure SQLAlchemy sessions to use it."""
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)


def list_discs(session: Session) -> list[Disc]:
    # TODO: Consider keeping this an iterator.
    return list(session.scalars(select(Disc)).all())


def get_disc(session: Session, name: str) -> Disc:
    try:
        return session.execute(select(Disc).filter_by(name=name)).scalar_one()
    except NoResultFound:
        disc = Disc(name=name)
        session.add(disc)
        session.flush()
        return disc
