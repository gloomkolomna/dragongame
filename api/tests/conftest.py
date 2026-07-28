import sys
import os

_TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test.db")
if os.path.exists(_TEST_DB_PATH):
    try:
        os.remove(_TEST_DB_PATH)
    except OSError:
        pass
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import config as _config
_config.ROBOKASSA_INV_ID_OFFSET = 0

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from db import get_db
from models import Base
from auth import get_current_admin

engine = create_engine(
    _config.DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from main import app
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_admin] = lambda: None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
