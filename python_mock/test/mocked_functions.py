"""Per-route mock behavior. One function per mocked route, named by `handler` in mock.toml.

Each function receives the ASGI `scope` (method, path, query, headers) and returns the JSON body.
mock.py checks at startup that every `handler` in mock.toml exists here, so a typo fails fast.
"""


def foobar(scope):
    return {"value": 42}
