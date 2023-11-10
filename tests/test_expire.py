from datetime import datetime, timedelta

import pytest
from loguru import logger

from expiringdictx import ExpiringDict


@pytest.fixture
def test_exdict():
    def log(key, value):
        logger.info(f"Operation: {key} = {value}")

    ex_dict = ExpiringDict[str, int](capacity=10, default_age=1, callback=log)
    yield ex_dict
    ex_dict.clear()


def test_io(test_exdict: ExpiringDict[str, int]):
    test_exdict["a"] = 1
    assert test_exdict["a"] == 1
    a = test_exdict.get_with_datetime("a")
    assert a
    assert a[1] <= datetime.now() + timedelta(seconds=1)

    test_exdict["b", 15] = 2
    assert test_exdict.get("b") == 2
    b = test_exdict.get_with_datetime("b")
    assert b
    assert datetime.now() + timedelta(seconds=10) < b[1] <= datetime.now() + timedelta(seconds=15)

    test_exdict["c", timedelta(minutes=1)] = 3
    c = test_exdict.get_with_datetime("c")
    assert c
    assert c[0] == 3
    assert c[1] >= datetime.now() + timedelta(seconds=60) - timedelta(seconds=1)

    test_exdict.clear()
    assert len(test_exdict) == 0

    # reach capacity
    for index, key in enumerate("abcdefghijk"):
        test_exdict[key] = index
    assert len(test_exdict) == 10
    assert "a" not in test_exdict
    assert "k" in test_exdict
    test_exdict.pop("k")
    assert "k" not in test_exdict
    assert test_exdict["b"] == 1
    test_exdict.popitem()
    assert "b" in test_exdict
    assert "c" not in test_exdict


def test_magic_methods(test_exdict: ExpiringDict[str, int]):
    test_exdict["a"] = 1
    test_exdict["b"] = 2
    test_exdict["c"] = 3

    assert len(test_exdict) == 3
    assert "a" in test_exdict
    for key in test_exdict:
        assert key in "abc"
    del test_exdict["a"]
    assert len(test_exdict) == 2
    assert "a" not in test_exdict


def test_expire(
    test_exdict: ExpiringDict[str, int],
):
    from time import sleep

    now = datetime.now()
    test_exdict["a"] = 1
    test_exdict["b", 15] = 2
    test_exdict["c", timedelta(minutes=1)] = 3
    assert len(test_exdict) == 3
    sleep(0.5)
    assert len(test_exdict) == 3
    sleep(0.5)
    assert len(test_exdict) == 2
    assert "a" not in test_exdict
    sleep(0.1)
    assert len(test_exdict) == 2

    test_exdict.refresh("b")
    assert len(test_exdict) == 2
    assert "b" in test_exdict
    assert timedelta(seconds=15 - 1.2) < (test_exdict.ttl("b") or timedelta(seconds=0)) <= timedelta(seconds=15)
    c = test_exdict.ddl("c")
    assert c
    assert c > now + timedelta(seconds=60 - 1.2)
    test_exdict.refresh("c", 30)
    c2 = test_exdict.ddl("c")
    assert c2
    assert c2 > now + timedelta(seconds=60 - 1.2)
    test_exdict.refresh("b", timedelta(seconds=30))
    assert (test_exdict.ttl("b") or timedelta(seconds=0)) > timedelta(seconds=15)


def test_create():
    keys = ["a", "b", "c"]
    d1 = ExpiringDict.fromkeys(keys, 1, 10)
    assert len(d1) == 3
    d2 = ExpiringDict.frommapping({"a": 1, "b": 2, "c": 3}, 10)
    assert len(d2) == 3
    d3 = ExpiringDict.fromexpiringdict(d2)
    assert len(d3) == 3
