from types import SimpleNamespace

from core import security as security_mod
from methods.announce import Annonce


class _FakeRepo:
    def __init__(self, get_value):
        self._get_value = get_value

    def __enter__(self):
        return self

    def __exit__(self, _type, _val, _tb):
        return False

    def get(self):
        return self._get_value()

    def get_one(self, _filter):
        return self._get_value()


def test_get_jwt_secret_caches_db_result(monkeypatch):
    security_mod.clear_jwt_secret_cache()
    calls = {"count": 0}

    def read_secret():
        calls["count"] += 1
        return "cached-secret"

    monkeypatch.setattr(
        security_mod,
        "SecurityRepository",
        lambda: _FakeRepo(read_secret),
    )
    assert security_mod.get_jwt_secret() == "cached-secret"
    assert security_mod.get_jwt_secret() == "cached-secret"
    assert calls["count"] == 1
    security_mod.clear_jwt_secret_cache()
    assert security_mod.get_jwt_secret() == "cached-secret"
    assert calls["count"] == 2
    security_mod.clear_jwt_secret_cache()


def test_announce_cache_skips_db_on_second_read(monkeypatch):
    Annonce.invalidate_cache()
    calls = {"count": 0}

    def read_setting():
        calls["count"] += 1
        return SimpleNamespace(value="hello")

    monkeypatch.setattr(
        "methods.announce.AppSettingsRepository",
        lambda: _FakeRepo(read_setting),
    )
    assert Annonce.get_text() == "hello"
    assert Annonce.get_header_value().startswith("base64:")
    assert Annonce.get_text() == "hello"
    assert calls["count"] == 1
    Annonce.invalidate_cache()
    assert Annonce.get_text() == "hello"
    assert calls["count"] == 2
    Annonce.invalidate_cache()


def test_background_threads_stay_off_when_disabled(monkeypatch):
    import threads

    monkeypatch.setenv("ENABLE_BACKGROUND_THREADS", "0")
    threads._background_threads_started = False
    threads._background_threads.clear()
    threads.start_background_threads()
    assert threads._background_threads_started is False
    assert threads._background_threads == []
