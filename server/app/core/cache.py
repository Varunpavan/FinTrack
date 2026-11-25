import time
from typing import Any, Optional, Dict, Tuple

# TTL in seconds
USER_CACHE_TTL = 300       # 5 minutes
DASHBOARD_CACHE_TTL = 60   # 1 minute
BUDGET_CACHE_TTL = 60      # 1 minute

_user_cache: Dict[int, Tuple[float, Any]] = {}
_dashboard_cache: Dict[int, Tuple[float, Any]] = {}
_budget_cache: Dict[int, Tuple[float, Any]] = {}


# --- User Cache ---
def get_cached_user(user_id: int) -> Optional[Any]:
    entry = _user_cache.get(user_id)
    if entry:
        ts, user = entry
        if time.time() - ts < USER_CACHE_TTL:
            return user
        _user_cache.pop(user_id, None)
    return None


def set_cached_user(user_id: int, user: Any):
    _user_cache[user_id] = (time.time(), user)


def invalidate_user_cache(user_id: int):
    _user_cache.pop(user_id, None)


# --- Dashboard Cache ---
def get_cached_dashboard(user_id: int) -> Optional[Any]:
    entry = _dashboard_cache.get(user_id)
    if entry:
        ts, data = entry
        if time.time() - ts < DASHBOARD_CACHE_TTL:
            return data
        _dashboard_cache.pop(user_id, None)
    return None


def set_cached_dashboard(user_id: int, data: Any):
    _dashboard_cache[user_id] = (time.time(), data)


def invalidate_dashboard_cache(user_id: int):
    _dashboard_cache.pop(user_id, None)


# --- Budget Cache ---
def get_cached_budget(user_id: int) -> Optional[Any]:
    entry = _budget_cache.get(user_id)
    if entry:
        ts, data = entry
        if time.time() - ts < BUDGET_CACHE_TTL:
            return data
        _budget_cache.pop(user_id, None)
    return None


def set_cached_budget(user_id: int, data: Any):
    _budget_cache[user_id] = (time.time(), data)


def invalidate_budget_cache(user_id: int):
    _budget_cache.pop(user_id, None)


def invalidate_all_user_caches(user_id: int):
    invalidate_user_cache(user_id)
    invalidate_dashboard_cache(user_id)
    invalidate_budget_cache(user_id)
