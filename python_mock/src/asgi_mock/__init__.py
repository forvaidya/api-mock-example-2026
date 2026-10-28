"""asgi_mock: mock routes of any ASGI app (FastAPI, Starlette) without changing the app.

How to operate
--------------
1. mock.toml: which routes (each is mocked OR disabled; unlisted routes run real)

    [[route]]
    method = "GET"
    path = "/positions"
    handler = "positions"      # mocked: my_mocks.positions(scope) returns the JSON body

    [[route]]
    method = "POST"
    path = "/orders"
    disabled = true            # disabled: 500, real handler never runs

2. my_mocks.py: what mocked routes return (one function per handler)

    def positions(scope):      # scope = ASGI request dict (method, path, query_string, headers)
        return {"net": [], "day": []}

3. Wrap your app once, in your server entrypoint:

    import asgi_mock, my_mocks
    app = asgi_mock.wrap(app, my_mocks, toml="path/to/mock.toml")

4. Run:  MOCK=true uvicorn main:app   -> mock mode (exactly "true", case-sensitive)
         uvicorn main:app             -> real mode (wrap returns your app untouched)

Behavior in mock mode: mocked -> handler body + `x-mock: true`; disabled -> 500 + `x-mock: true`;
unlisted -> your real app. A handler in the toml missing from your module fails at startup.
The toml is re-read per request (edits apply live); handler code changes need a restart.
"""
import json
import os
import tomllib

__all__ = ["wrap", "enabled"]  # public API; MockMiddleware is internal

MOCK_FILE = os.getenv("MOCK_FILE", "mock.toml")


def enabled() -> bool:
    return os.getenv("MOCK") == "true"  # exactly "true", case-sensitive; anything else is real


class MockMiddleware:
    def __init__(self, app, functions, toml=MOCK_FILE):
        self.app = app
        self.functions = functions
        self.toml = toml
        self._routes()  # fail fast: bad toml or unknown handler stops startup

    def _routes(self):
        # ponytail: re-reads toml per request so edits apply live; cache it if latency matters
        with open(self.toml, "rb") as f:
            routes = {(r.get("method", "GET").upper(), r["path"]): r for r in tomllib.load(f).get("route", [])}
        for key, r in routes.items():
            if r.get("disabled"):  # disabled: never touches functions, so nothing to check
                continue
            if not callable(getattr(self.functions, r.get("handler") or "", None)):
                raise ValueError(f"{self.toml} {key}: handler {r.get('handler')!r} not found in {self.functions.__name__}")
        return routes

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            route = self._routes().get((scope["method"], scope["path"]))
            if route:
                if route.get("disabled"):  # disabled in mock mode: refuse, never call the real handler
                    status, data = 500, {"error": f"{scope['method']} {scope['path']} is disabled in mock mode"}
                else:  # mocked: per-route behavior lives in the functions module
                    status, data = route.get("status", 200), getattr(self.functions, route["handler"])(scope)
                body = json.dumps(data).encode()
                await send({"type": "http.response.start", "status": status,
                            "headers": [(b"content-type", b"application/json"), (b"x-mock", b"true")]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


def wrap(app, functions, toml=MOCK_FILE):
    return MockMiddleware(app, functions, toml) if enabled() else app
