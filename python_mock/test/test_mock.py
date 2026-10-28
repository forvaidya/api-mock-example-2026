# CUSTOMER tests: good, disabled and ignored mock against the customer's app, toml and functions.
import os
import tempfile
from pathlib import Path

import asgi_mock as mock  # OURS (installed package)
from fastapi.testclient import TestClient

import mocked_functions  # CUSTOMER
from app import app  # CUSTOMER

HERE = Path(__file__).resolve().parent


def client(mock_on):
    os.environ["MOCK"] = "true" if mock_on else "false"
    return TestClient(mock.wrap(app, mocked_functions, toml=HERE / "mock.toml"))


def test_good_mock():
    """foobar: real when unmocked, mocked handler when MOCK=true."""
    r = client(False).get("/foobar")
    assert "x-mock" not in r.headers and isinstance(r.json()["value"], int)
    r = client(True).get("/foobar")
    assert r.json() == {"value": 42} and r.headers["x-mock"] == "true"


def test_disabled_mock():
    """sensitive: works unmocked, 500 when MOCK=true (real handler never runs)."""
    r = client(False).post("/sensitive")
    assert r.status_code == 200 and r.json() == {"message": "sensitive done"}
    r = client(True).post("/sensitive")
    assert r.status_code == 500 and "disabled" in r.json()["error"] and r.headers["x-mock"] == "true"


def test_ignored_mock():
    """time: not in mock.toml, so the real handler runs in both modes."""
    for mock_on in (False, True):
        r = client(mock_on).get("/time")
        assert "now" in r.json() and "x-mock" not in r.headers, mock_on


def test_mock_switch_exact():
    """only exact MOCK=true enables the mock."""
    for v in ["True", "TRUE", "1", "yes", " true"]:
        os.environ["MOCK"] = v
        assert not mock.enabled(), v


def test_fail_fast():
    """a handler named in toml but missing from mocked_functions.py stops startup."""
    bad = Path(tempfile.mkdtemp()) / "bad.toml"
    bad.write_text('[[route]]\npath = "/x"\nhandler = "nope"\n')
    try:
        mock.MockMiddleware(app, mocked_functions, toml=bad)
        raise AssertionError("bad handler did not fail at startup")
    except ValueError as e:
        assert "nope" in str(e)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"pass  {name}")
    print("ok")
