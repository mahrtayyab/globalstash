# globalstash

Thread-safe, process-wide global state you can import from **any module at any depth**, with no `sys.path` tricks.

```bash
pip install globalstash
```

## Usage

```python
from globalstash import g

# anywhere in your app
g.db_pool = create_pool()
g["config"] = {"debug": True}

g.get("missing", "default")
g.setdefault("cache", {})
g.update(env="prod", version="1.0")
"db_pool" in g
del g.db_pool
```

Because Python caches modules, every `from globalstash import g` returns the same object.

### Atomic and compound operations

```python
g.incr("requests")          # atomic counter

with g.lock:                # read-modify-write
    g.total = g.total + 1
```

### Named namespaces

```python
from globalstash import get_state

cache = get_state("cache")   # same name -> same object everywhere
cache.ttl = 60
```

### Tests

```python
with g.temporary(debug=True):
    ...   # values restored on exit
```

## Notes

- Method names (`get`, `pop`, `update`, ...) can't be used as attribute keys; use `g["get"]`.
- State lives **per process**. Gunicorn/Uvicorn workers each have their own copy. Use Redis or a database for state shared across processes.
- For per-request state (like `flask.g`), use `contextvars` instead.

## License

MIT
