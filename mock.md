# Main Rule

Always use uv, own venv and maintain requirements.txt with version anchored 

# Key takeaway

**The server starts in exactly one place: `uvicorn.run` in `serve.py`.** `app.py` is only setup (routes), so importing it starts nothing.
`serve.py` is the only file that joins app + mock: `asgi = mock.wrap(app, mocked_functions, toml="mock.toml")` then `uvicorn.run(asgi)`.
Hono counterpart: `Bun.serve` in `hono/test/serve.ts`.

# Objective
prototype to use mock api response from the same Interface based on an env var MOCK=true.

## workings
A fast api server with an endpoint /foobar which return a random number. (main behavior) 
Mock - Must return a fixed number configurable using tomal. 

A wapper must be no code change. any mock behavior to be changed from toml. Mock invocation should happen based on env VAR or MACK=trye uv ... 

# Tech Stack
fast api. 

# Outcome
should be mock and unmock with variable change

## Extended outcome - want to apply this for real apis 


# Implementation

| File | Role |
|------|------|
| `python_mock/src/asgi_mock/` | **OURS**: the framework, packaged as the `asgi-mock` wheel (stdlib only, no dependencies). Routes in the customer's toml are mocked (their handler) or disabled (500, `x-mock: true`); all other routes pass through. Never edited by customers; `help(asgi_mock)` shows how to operate. |
| `python_mock/test/` | **CUSTOMER** (today a demo; tomorrow Kite, Groww, Dhan…). Everything below is theirs: |
| `python_mock/test/app.py` | their real FastAPI app: `/foobar`, `/time`, `POST /sensitive`. Knows nothing about mocks. |
| `python_mock/test/serve.py` | their server: `mock.wrap(app, mocked_functions, toml=...)` + uvicorn. The only file joining their app with our framework. |
| `python_mock/test/mock.toml` | their routes: `handler` (mocked) or `disabled = true` (500). Unlisted routes pass through. Re-read per request. |
| `python_mock/test/mocked_functions.py` | their mock behavior: one function per `handler`. Unknown handler fails at startup. |
| `python_mock/test/test_mock.py` | their tests: good mock, disabled mock, ignored mock, exact switch, fail-fast. |

## Setup
```sh
cd python_mock && uv venv .venv && uv pip install -r requirements.txt
cd python_mock && uv build --wheel                                         # -> dist/asgi_mock-0.1.0-py3-none-any.whl
cd python_mock && uv pip install dist/asgi_mock-0.1.0-py3-none-any.whl     # the framework, as a customer would install it
```
Adding a dep: `uv pip install <pkg> && uv pip freeze > requirements.txt`

## Run
```sh
cd python_mock && uv run test/serve.py            # real   → {"value": <random>}
cd python_mock && MOCK=true uv run test/serve.py  # mocked → {"value": 42}
cd python_mock && PORT=8765 uv run test/serve.py  # port 8000 is taken by OrbStack on this machine
cd python_mock && uv run --with-requirements requirements.txt test/test_mock.py   # 5 pass, prints "ok"
```

## Route behavior (example)
| Route | not mocked | `MOCK=true` | in `mock.toml` |
|---|---|---|---|
| `GET /foobar` | real random | mocked `{"value": 42}` | `handler = "foobar"` |
| `GET /time` | real | real (pass-through) | not listed |
| `POST /sensitive` | real `{"message": "sensitive done"}` | 500, refused | `disabled = true` |

## Applying to real APIs
Any ASGI app (FastAPI/Starlette) gets mocking by wrapping it once: `app = mock.wrap(app, my_functions, toml="mock.toml")`. The framework (`python_mock/src/asgi_mock/`) is closed; only the toml and the functions module are external. Then list endpoints in `mock.toml` (`handler` or `disabled = true`) and write each handler in `mocked_functions.py`. Unlisted endpoints stay real, so you can mock one route at a time.

Not yet supported (add when needed): path params / query matching in `mock.toml` (a handler can read `scope` itself), mocking *outbound* calls your app makes to a third-party API (that needs an httpx transport hook instead of an ASGI wrapper).
