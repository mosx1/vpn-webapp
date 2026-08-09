from unittest.mock import patch

from sqlalchemy import Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from connect import engine as root_engine
from db.common import BaseRepository
from db.connect import create_session, engine


class _Base(DeclarativeBase):
    pass


class DummyModel(_Base):
    __tablename__ = "dummy_repo_session_pool_test"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


def test_create_session_uses_shared_engine() -> None:
    sessions = [create_session() for _ in range(20)]
    try:
        assert all(session.bind is engine for session in sessions)
    finally:
        for session in sessions:
            session.close()


def test_repositories_do_not_create_engines() -> None:
    with patch("db.connect.create_engine") as mocked_create_engine:
        repos = [BaseRepository(DummyModel) for _ in range(20)]
        try:
            assert mocked_create_engine.call_count == 0
            assert all(repo.session.bind is engine for repo in repos)
        finally:
            for repo in repos:
                repo.session.close()


def test_root_connect_reuses_db_engine() -> None:
    assert root_engine is engine
