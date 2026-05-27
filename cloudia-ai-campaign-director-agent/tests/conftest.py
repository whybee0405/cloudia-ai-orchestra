"""pytest configuration and shared fixtures."""
import os
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Valid Fernet key (32 url-safe base64 bytes) — test only
_TEST_FERNET_KEY = "ExGL52zjdS3UXmKLgily-igHF4XPj8In1MjDdWlxWrk="

os.environ["ENCRYPTION_KEY"] = _TEST_FERNET_KEY
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.db.models import Base


def _enable_sqlite_fk(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="function")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    event.listen(eng, "connect", _enable_sqlite_fk)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture(scope="function")
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def mock_claude():
    """Returns a mock Claude client that returns a canned response."""
    with patch("backend.ai.claude.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        response = MagicMock()
        response.content = [MagicMock(text="Mocked Claude response")]
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        mock_client.messages.create.return_value = response
        yield mock_client


@pytest.fixture
def mock_dalle():
    """Returns a mock DALL-E client."""
    with patch("backend.ai.dalle.openai.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        response = MagicMock()
        response.data = [MagicMock(url="https://example.com/test_image.png", b64_json=None)]
        mock_client.images.generate.return_value = response
        yield mock_client


@pytest.fixture
def mock_storage():
    """Returns a mock MinIO storage."""
    with patch("backend.media.storage") as mock_storage:
        mock_storage.upload = MagicMock(return_value=None)
        mock_storage.download = MagicMock(return_value=b"fake_bytes")
        mock_storage.signed_url = MagicMock(return_value="https://minio.local/test-file")
        mock_storage.object_path = MagicMock(return_value="1/campaigns/1/raw/images/test.jpg")
        yield mock_storage


@pytest.fixture
def mock_meta_platform():
    """Returns a mock Meta platform client."""
    with patch("backend.platforms.meta.MetaPlatform") as mock_cls:
        mock_p = MagicMock()
        mock_cls.return_value = mock_p
        mock_p.publish_instagram_image.return_value = "17841234567890"
        mock_p.publish_instagram_reel.return_value = "17841234567891"
        mock_p.publish_facebook_post.return_value = "123456789_987654321"
        mock_p.publish_whatsapp_broadcast.return_value = "wamid.test123"
        yield mock_p


@pytest.fixture
def mock_redis():
    """Returns an in-memory mock Redis client."""
    store = {}

    class FakeRedis:
        def setex(self, key, ttl, value):
            store[key] = value

        def get(self, key):
            return store.get(key)

        def delete(self, key):
            store.pop(key, None)

        def exists(self, key):
            return key in store

    return FakeRedis()
