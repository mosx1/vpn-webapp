from threading import Lock
from time import monotonic

from db.repository.security import SecurityRepository

_JWT_SECRET_TTL_SECONDS = 60.0
_jwt_secret_lock = Lock()
_cached_jwt_secret: str | None = None
_cached_jwt_secret_at: float = 0.0


def get_jwt_secret() -> str:
    """
        Секрет JWT из БД с коротким TTL-кэшем, чтобы /sub не ходил в Postgres на каждый запрос.
    """
    global _cached_jwt_secret, _cached_jwt_secret_at
    now = monotonic()
    with _jwt_secret_lock:
        if (
            _cached_jwt_secret is not None
            and now - _cached_jwt_secret_at < _JWT_SECRET_TTL_SECONDS
        ):
            return _cached_jwt_secret

    with SecurityRepository() as repo:
        secret = repo.get()

    with _jwt_secret_lock:
        _cached_jwt_secret = secret
        _cached_jwt_secret_at = monotonic()
    return secret


def clear_jwt_secret_cache() -> None:
    global _cached_jwt_secret, _cached_jwt_secret_at
    with _jwt_secret_lock:
        _cached_jwt_secret = None
        _cached_jwt_secret_at = 0.0


def is_valid_security_key(key: str) -> bool:
    return get_jwt_secret() == key


def is_valid_jwt(key: str) -> bool:
    pass
