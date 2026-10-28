# Hono version (same prototype, for comparison)

Runtime: **Bun** (runs TypeScript directly, built-in TOML parser + test runner, so no extra deps besides `hono`).

## Setup / run
```sh
cd hono
bun install                      # versions pinned exactly in package.json + bun.lock
bun test/serve.ts                # real   → {"value": <random>}
MOCK=true bun test/serve.ts      # mocked → {"value": 42}, header x-mock: true
PORT=8766 MOCK=true bun test/serve.ts
bun test                         # 5 pass
```
Adding a dep: `bun add --exact <pkg>` (the `requirements.txt` equivalent is `package.json` + `bun.lock`).

## Python ↔ Hono, file by file

| Python | Hono | Note |
|--------|------|------|
| `python_mock/test/app.py` | `test/app.ts` | `@app.get("/foobar")` → `app.get("/foobar", (c) => c.json(...))` |
| `python_mock/src/asgi_mock/` | `mock.ts` | OURS: the framework; same `enabled()`, same `wrap(app, functions, toml)` |
| `python_mock/test/serve.py` | `test/serve.ts` | `uvicorn.run(asgi)` → `Bun.serve({ fetch: server.fetch })` |
| `python_mock/test/mock.toml` | `test/mock.toml` | identical format (`handler` / `disabled`) |
| `python_mock/test/mocked_functions.py` | `test/mocked_functions.ts` | one function per mocked route; `getattr(mod, name)` → `handlers[name]` |
| `python_mock/test/test_mock.py` | `test/mock.test.ts` | `assert` → `expect(...)` |
| `uv` + `requirements.txt` | `bun` + `package.json`/`bun.lock` | |

## The one real difference: the app interface

| | Python (FastAPI) | Hono |
|---|---|---|
| What the server calls | ASGI: `await app(scope, receive, send)` | `app.fetch(request)` → `Response` |
| Request path | `scope["path"]` | `new URL(req.url).pathname` |
| Send mock reply | two `send()` messages (start + body) | `return Response.json(data, {status, headers})` |
| Forward to real app | `await self.app(scope, receive, send)` | `return app.fetch(req)` |
| Wrapper shape | class `MockMiddleware` with `__call__` | plain function returning a function |

The Hono side is simpler because `fetch` is "request in, response out". ASGI streams messages through `send`.
Flow is otherwise identical: `serve.ts` is the only file joining `app` and `mock`; `MOCK` is read once at startup in `wrap()`, `mock.toml` on every request.
