# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
from app.database import get_engine
from app.database import Base


def test_init_and_drop_creates_engine():
    engine = get_engine("sqlite:///./test_db_temp.sqlite")
    Base.metadata.create_all(bind=engine)
    Base.metadata.drop_all(bind=engine)
