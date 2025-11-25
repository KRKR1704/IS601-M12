# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
from sqlalchemy import create_engine
from importlib import reload

import app.database_init as db_init
from app.database import get_engine
from app.database import Base


def test_init_and_drop_monkeypatched_engine(tmp_path, monkeypatch):
    # Create a temporary sqlite file engine
    path = tmp_path / "tempdb.sqlite"
    engine = get_engine(database_url=f"sqlite:///{path}")

    # Monkeypatch the engine attribute in the database_init module
    monkeypatch.setattr(db_init, "engine", engine)

    # Call init and drop; should operate on our temp engine
    db_init.init_db()
    # verify tables exist
    Base.metadata.create_all(bind=engine)
    db_init.drop_db()
