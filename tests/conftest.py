# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
import socket
import subprocess
import time
import logging
from typing import Generator, Dict, List
from contextlib import contextmanager

import pytest
import requests
from faker import Faker
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from playwright.sync_api import sync_playwright, Browser, Page

from app.database import Base, get_engine, get_sessionmaker
from app.models.user import User
from app.core.config import settings
from app.database_init import init_db, drop_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

fake = Faker()
Faker.seed(12345)

import os

use_postgres = os.getenv("TEST_DATABASE", "sqlite").lower() == "postgres"
if use_postgres:
    test_engine = get_engine(database_url=settings.DATABASE_URL)
else:
    # File-based SQLite database so subprocess server and test runner share the DB
    test_engine = get_engine(database_url="sqlite:///./test_db.sqlite")

TestingSessionLocal = get_sessionmaker(engine=test_engine)

def create_fake_user() -> Dict[str, str]:
    """Generate a dictionary of fake user data for testing."""
    return {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "username": fake.unique.user_name(),
        "password": fake.password(length=12)
    }

@contextmanager
def managed_db_session():
    """Context manager for safe database session handling."""
    session = TestingSessionLocal()
    try:
        yield session
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

def wait_for_server(url: str, timeout: int = 30) -> bool:
    """
    Wait for the server to be ready by repeatedly issuing GET requests until
    we receive a 200 status code or hit the timeout.
    """
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    return False

class ServerStartupError(Exception):
    """Raised when the test server fails to start properly."""
    pass

@pytest.fixture(scope="session", autouse=True)
def setup_test_database(request):
    """
    Set up the test database before the session starts, and tear it down after tests
    unless --preserve-db is provided.
    """
    logger.info("Setting up test database...")
    try:
        # Create all tables on the test engine (avoids using the app global engine)
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)
        logger.info("Test database initialized (test engine).")
    except Exception as e:
        logger.error(f"Error setting up test database: {str(e)}")
        raise

    yield  # Tests run after this

    preserve_flag = getattr(request.config, "option", None)
    preserve = False
    if preserve_flag is not None:
        preserve = getattr(request.config.option, "preserve_db", False)

    if not preserve:
        logger.info("Dropping test database tables (test engine)...")
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """
    Provide a test-scoped database session. Commits after a successful test;
    rolls back if an exception occurs.
    """
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

@pytest.fixture
def fake_user_data() -> Dict[str, str]:
    """Provide fake user data."""
    return create_fake_user()

@pytest.fixture
def test_user(db_session: Session) -> User:
    """
    Create and return a single test user in the database.
    """
    user_data = create_fake_user()
    user = User(**user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    logger.info(f"Created test user ID: {user.id}")
    return user

@pytest.fixture
def seed_users(db_session: Session, request) -> List[User]:
    """
    Seed multiple test users in the database. By default, 5 users are created
    unless a 'param' value is provided (e.g., via @pytest.mark.parametrize).
    """
    num_users = getattr(request, "param", 5)
    users = [User(**create_fake_user()) for _ in range(num_users)]
    db_session.add_all(users)
    db_session.commit()
    logger.info(f"Seeded {len(users)} users.")
    return users

def find_available_port() -> int:
    """Find an available port for the test server by binding to port 0."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

@pytest.fixture(scope="session")
def fastapi_server():
    """
    Start a FastAPI test server in a subprocess. If the chosen port (default: 8000)
    is already in use, find another available port. Wait until the server is up
    before yielding its base URL.
    """
    base_port = 8000
    server_url = f'http://127.0.0.1:{base_port}/'

    # Check if port is free; if not, pick an available port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', base_port)) == 0:
            base_port = find_available_port()
            server_url = f'http://127.0.0.1:{base_port}/'

    logger.info(f"Starting FastAPI server on port {base_port}...")

    process = subprocess.Popen(
        ['uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(base_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd='.'
    )

    health_url = f"{server_url}health"
    if not wait_for_server(health_url, timeout=30):
        stderr = process.stderr.read()
        logger.error(f"Server failed to start. Uvicorn error: {stderr}")
        process.terminate()
        raise ServerStartupError(f"Failed to start test server on {health_url}")

    logger.info(f"Test server running on {server_url}.")
    yield server_url

    logger.info("Stopping test server...")
    process.terminate()
    try:
        process.wait(timeout=5)
        logger.info("Test server stopped.")
    except subprocess.TimeoutExpired:
        process.kill()
        logger.warning("Test server forcefully stopped.")

@pytest.fixture(scope="session")
def browser_context():
    """Provide a Playwright browser context for UI tests (session-scoped)."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        logger.info("Playwright browser launched.")
        try:
            yield browser
        finally:
            browser.close()
