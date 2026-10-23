
from unittest.mock import MagicMock, patch

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine, get_db


def test_database_url_is_configured():
    assert settings.DATABASE_URL.startswith("postgresql+psycopg://")
    assert settings.DATABASE_URL.endswith("/gatekeep")


def test_database_engine_is_created():
    assert isinstance(engine, Engine)
    assert engine.dialect.name == "postgresql"


def test_session_factory_is_configured():
    session = SessionLocal()

    try:
        assert isinstance(session, Session)
    finally:
        session.close()


def test_base_has_metadata():
    assert Base.metadata is not None


def test_get_db_closes_session():
    mock_session = MagicMock()

    with patch("app.database.SessionLocal", return_value=mock_session):
        generator = get_db()
        session = next(generator)

        assert session is mock_session

        generator.close()

        mock_session.close.assert_called_once()
