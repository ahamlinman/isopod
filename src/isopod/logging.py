import logging


def configure():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        datefmt="%F %T",
    )

    # Work around SQLAlchemy adding their own handler for echo=True, even though we
    # already have one at the root.
    logging.getLogger("sqlalchemy.engine.Engine").addHandler(logging.NullHandler())
