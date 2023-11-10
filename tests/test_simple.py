from time import sleep
from datetime import timedelta

import pytest

from expiringdictx import SimpleCache


@pytest.fixture
def test_scdict():
    ex_dict = SimpleCache()
    yield ex_dict
    ex_dict.clear()


def test_get_set(
    test_scdict: SimpleCache,
):
    test_scdict["a", timedelta(seconds=1)] = 1
    assert test_scdict["a"] == 1
    assert test_scdict.get("a") == 1
    assert test_scdict.get("a", value_convert_func=str) == "1"
    test_scdict["b"] = "2"
    assert test_scdict["b"] == "2"
    assert test_scdict.get("b", value_convert_func=int) == 2
    test_scdict["c"] = (3,)
    assert test_scdict["c"] == (3,)
    test_scdict.set("d", 4, timedelta(seconds=1))

    sleep(1)
    assert test_scdict["a"] is None
    assert test_scdict.get("a") is None
