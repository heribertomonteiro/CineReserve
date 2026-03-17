import hashlib

from django.core.cache import cache

MOVIE_SESSIONS_CACHE_TTL = 60
SEAT_MAP_CACHE_TTL = 30


def movie_sessions_cache_key(movie_id: int, full_path: str) -> str:
    return _build_cache_key(f"movie:{movie_id}:sessions", full_path)


def session_seat_map_cache_key(session_id: int, full_path: str) -> str:
    return _build_cache_key(f"session:{session_id}:seat-map", full_path)


def invalidate_movie_sessions_cache(movie_id: int) -> None:
    pattern = f"movie:{movie_id}:sessions:*"
    _invalidate_by_pattern(pattern)


def invalidate_session_seat_map_cache(session_id: int) -> None:
    pattern = f"session:{session_id}:seat-map:*"
    _invalidate_by_pattern(pattern)


def invalidate_seat_map_cache(session_id: int) -> None:
    invalidate_session_seat_map_cache(session_id)


def _invalidate_by_pattern(pattern: str) -> None:
    delete_pattern = getattr(cache, "delete_pattern", None)

    if callable(delete_pattern):
        delete_pattern(pattern)
        return

    # Fallback simples caso o backend nao suporte delete por padrao.
    cache.clear()


def _build_cache_key(prefix: str, raw: str) -> str:
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"
