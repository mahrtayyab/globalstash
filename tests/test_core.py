import threading

import pytest

from globalstash import GlobalState, g, get_state


@pytest.fixture(autouse=True)
def _clean():
    g.clear()
    yield
    g.clear()


def test_attr_and_item_access():
    g.a = 1
    g["b"] = 2
    assert g.a == 1 and g["a"] == 1 and g.b == 2
    assert "a" in g and len(g) == 2


def test_missing_attr_raises():
    with pytest.raises(AttributeError):
        g.nope


def test_get_pop_setdefault_update():
    assert g.get("x", 5) == 5
    assert g.setdefault("x", 1) == 1
    assert g.setdefault("x", 2) == 1
    g.update(y=3, z=4)
    assert g.pop("y") == 3
    assert g.pop("missing", None) is None
    assert g.to_dict() == {"x": 1, "z": 4}


def test_delete():
    g.a = 1
    del g.a
    assert "a" not in g


def test_same_object_across_imports():
    from globalstash import g as g2
    g.v = 1
    assert g2.v == 1


def test_named_registry():
    assert get_state("app") is get_state("app")
    assert get_state("app") is not get_state("other")


def test_temporary():
    g.a = 1
    with g.temporary(a=2, b=3):
        assert g.a == 2 and g.b == 3
    assert g.a == 1 and "b" not in g


def test_incr_is_atomic_across_threads():
    def work():
        for _ in range(2000):
            g.incr("n")

    threads = [threading.Thread(target=work) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert g.n == 16000


def test_lock_compound_op():
    g.total = 0

    def work():
        for _ in range(2000):
            with g.lock:
                g.total = g.total + 1

    threads = [threading.Thread(target=work) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert g.total == 16000


def test_independent_instances():
    a, b = GlobalState(x=1), GlobalState()
    assert "x" not in b and a.x == 1
