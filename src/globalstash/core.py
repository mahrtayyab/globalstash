"""Core implementation of globalstash."""
from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Tuple

_MISSING = object()


class GlobalState:
    """A thread-safe namespace for process-wide global values.

    Values can be accessed as attributes or as items::

        g.db = create_pool()
        g["db"]
        g.get("missing", None)

    Individual operations are atomic. For compound operations
    (read-modify-write), use ``incr`` or the ``lock`` context manager::

        with g.lock:
            g.total = g.total + 1

    Note: names of methods (``get``, ``pop``, ``update``...) can't be used
    as attribute keys; use item access (``g["get"]``) for those.
    """

    __slots__ = ("_data", "_lock")

    def __init__(self, **initial: Any) -> None:
        object.__setattr__(self, "_data", dict(initial))
        object.__setattr__(self, "_lock", threading.RLock())

    # ---- attribute access -------------------------------------------------
    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") or name in ("_data", "_lock"):
            raise AttributeError(name)
        with self._lock:
            try:
                return self._data[name]
            except KeyError:
                raise AttributeError(
                    f"global state has no attribute {name!r}"
                ) from None

    def __setattr__(self, name: str, value: Any) -> None:
        with self._lock:
            self._data[name] = value

    def __delattr__(self, name: str) -> None:
        with self._lock:
            try:
                del self._data[name]
            except KeyError:
                raise AttributeError(name) from None

    # ---- item access ------------------------------------------------------
    def __getitem__(self, key: str) -> Any:
        with self._lock:
            return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def __delitem__(self, key: str) -> None:
        with self._lock:
            del self._data[key]

    def __contains__(self, key: object) -> bool:
        with self._lock:
            return key in self._data

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            return iter(list(self._data))

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __repr__(self) -> str:
        with self._lock:
            return f"GlobalState({self._data!r})"

    # ---- dict-like helpers ------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self[key] = value

    def setdefault(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.setdefault(key, default)

    def pop(self, key: str, default: Any = _MISSING) -> Any:
        with self._lock:
            if default is _MISSING:
                return self._data.pop(key)
            return self._data.pop(key, default)

    def update(self, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            self._data.update(*args, **kwargs)

    def keys(self) -> Tuple[str, ...]:
        with self._lock:
            return tuple(self._data.keys())

    def values(self) -> Tuple[Any, ...]:
        with self._lock:
            return tuple(self._data.values())

    def items(self) -> Tuple[Tuple[str, Any], ...]:
        with self._lock:
            return tuple(self._data.items())

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Return a shallow copy of the current state."""
        with self._lock:
            return dict(self._data)

    # ---- atomic / compound operations ------------------------------------
    def incr(self, key: str, amount: int = 1, default: int = 0) -> int:
        """Atomically add ``amount`` to ``key`` and return the new value."""
        with self._lock:
            value = self._data.get(key, default) + amount
            self._data[key] = value
            return value

    @property
    def lock(self) -> "threading.RLock":  # type: ignore[valid-type]
        """The re-entrant lock, for compound operations: ``with g.lock: ...``"""
        return self._lock

    @contextmanager
    def temporary(self, **overrides: Any) -> Iterator["GlobalState"]:
        """Temporarily override values (handy in tests); restored on exit."""
        with self._lock:
            saved = {k: self._data.get(k, _MISSING) for k in overrides}
            self._data.update(overrides)
        try:
            yield self
        finally:
            with self._lock:
                for k, v in saved.items():
                    if v is _MISSING:
                        self._data.pop(k, None)
                    else:
                        self._data[k] = v


# ---- default instance and named registry ---------------------------------
g = GlobalState()

_registry: Dict[str, GlobalState] = {}
_registry_lock = threading.Lock()


def get_state(name: str) -> GlobalState:
    """Return the shared ``GlobalState`` registered under ``name``.

    The same name always returns the same object, so independent libraries
    or components can each keep their own namespace without collisions.
    """
    with _registry_lock:
        state = _registry.get(name)
        if state is None:
            state = _registry[name] = GlobalState()
        return state
