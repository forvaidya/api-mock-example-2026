# asgi-mock: user manual

Mock routes of your ASGI app (FastAPI, Starlette) without changing the app. Mocking is switched on by the environment variable `MOCK=true`. Behaviour lives in two files you write: `mock.toml` and `mocked_functions.py`.

## 1. Install

The package is not on PyPI yet. Install it from git, pinned to a commit or tag:

```sh
pip install "asgi-mock @ git+https://github.com/forvaidya/api-mock-example-2026@<commit-or-tag>#subdirectory=python_mock"
```

Requires Python 3.11 or newer. No other dependencies. Your app still brings its own FastAPI or Starlette.

## 2. Wrap your app

In your server entrypoint (any `.py` file), wrap the app once:

```python
import asgi_mock as mock
import uvicorn

import mocked_functions   # your mock behaviour
from main import app      # your real app, with no mock code

asgi = mock.wrap(app, mocked_functions, toml="mock.toml")

if __name__ == "__main__":
    uvicorn.run(asgi, host="127.0.0.1", port=8000)
```

Run the wrapped object, not the raw `app`. If the server runs the raw app, nothing is mocked and no error is shown.

`wrap()` returns your app unchanged when `MOCK` is not exactly `"true"`, so the same line is safe in real mode.

## 3. Describe the routes: `mock.toml`

```toml
[[route]]
method = "GET"          # default "GET"
path = "/weather"       # exact path match
handler = "weather"     # mocked: function `weather` in mocked_functions.py
status = 200            # optional, default 200 (mocked routes only)

[[route]]
method = "POST"
path = "/orders"
disabled = true         # disabled: always 500, real handler never runs
```

- Each route is either mocked (`handler`) or disabled (`disabled = true`).
- Routes not listed pass through to your real app.
- Matching is by method and exact path. Path parameters and query strings are not matched.
- The file is re-read on every request, so edits apply immediately.

## 4. Write the mock functions: `mocked_functions.py`

```python
def weather(scope):
    return {"city": "Pune", "temp_c": 31}
```

- The function name must equal the `handler` in `mock.toml`. A missing name stops the server at startup with a `ValueError` naming the route and the module.
- It receives the ASGI `scope` dict. Use `scope["method"]`, `scope["path"]`, `scope["query_string"]` or `scope["headers"]` to branch.
- It must be a plain `def`. An `async def` is not supported, because its result is not awaited.
- Return a JSON-serializable value (dict, list, string, number).
- You may import anything you need: fixtures, files, your own helpers.

## 5. Run

```sh
MOCK=true python serve.py    # mocked
python serve.py              # real
```

- `MOCK` must be exactly `true`, lowercase. `TRUE`, `1` or `yes` mean real mode.
- `MOCK_FILE` sets the default toml path only when `wrap()` is called without `toml=`.

## What you get back

| Route case | Response |
|---|---|
| Mocked (`handler`) | your function's return value as JSON, with the given `status`, plus header `x-mock: true` |
| Disabled | `500` with `{"error": "... is disabled in mock mode"}` and `x-mock: true`. Your real handler is not called |
| Not listed | your real app's response, with no `x-mock` header |

The `x-mock: true` header tells you a response came from the mock.

## Testing your own code

Build the wrapped app in your tests with `MOCK` set. `wrap()` reads `MOCK` when it is called, so set the variable before calling it:

```python
import os
from fastapi.testclient import TestClient
import asgi_mock as mock

os.environ["MOCK"] = "true"
client = TestClient(mock.wrap(app, mocked_functions, toml="mock.toml"))
assert client.get("/weather").headers["x-mock"] == "true"
```

Clear `MOCK` afterwards if other tests need real mode.

## Troubleshooting

- **No `x-mock` header on a route you mocked:** the server is running the raw app, or `MOCK` is not exactly `true`.
- **Server fails at startup with `ValueError`:** a `handler` in `mock.toml` has no matching function in your module. Check the spelling.
- **500 with "disabled in mock mode":** the route is `disabled = true` in `mock.toml`. This is expected.
- **Toml edit not taking effect:** check the file path. Edits apply per request, but changed Python code needs a restart.

## Limits

- Mocks only the routes of the app you wrap. Outbound calls your app makes to third-party APIs are not mocked.
- No path-parameter or query matching in `mock.toml`. Branch on `scope` inside the function.
- Mock functions must be synchronous.
- Changing `MOCK` on a running server has no effect. Restart it.

## Your responsibilities

The framework switches routes on and off. It does not decide what is safe or correct. These are yours:

- **Mock data must match the real API.** The framework does not check the shape of what your function returns. If the real API changes, update `mocked_functions.py` too.
- **Choose mocked or disabled for every route that matters.** Anything with side effects (orders, payments, writes, emails) should be `disabled = true` unless you have a deliberate mock for it. The framework cannot tell which routes are dangerous.
- **Never set `MOCK=true` where real money or real data is at stake.** The framework does not stop you from doing it. Use it in tests and local runs only, and make sure production does not have it set.
- **Handle outbound calls yourself.** If your app calls a third-party API, that call is real even in mock mode. Mock it in your own code (for example, by injecting a fake client), or accept that it runs.
- **Keep mock data free of secrets and real personal data.** The mock files are plain text in your repository.
- **Pin the framework version** in your install line, and re-run your tests after each upgrade.
- **Keep the real app free of mock code.** Only the entrypoint should import `asgi_mock`. If you find yourself adding `if MOCK:` to your routes, the design has drifted.

## How to read the test folder

The example in `python_mock/test/` is a complete customer setup. It is the template you copy. Read it in this order:

1. **`app.py`**: the real app with three routes: `/foobar`, `/time`, `POST /sensitive`. This is what gets mocked. It contains no mock code.
2. **`mock.toml`**: the routing table. `/foobar` is mocked (`handler = "foobar"`), `POST /sensitive` is disabled, and `/time` is not listed, so it passes through.
3. **`mocked_functions.py`**: the fake responses. One function per `handler`. `foobar` returns `{"value": 42}`.
4. **`serve.py`**: the main entry point, used for both production and local runs. It wraps the app once with `mock.wrap(...)` and starts uvicorn. Mocking is decided by the environment: production runs it without `MOCK`, so the app is served for real. This is the only file that imports `asgi_mock`. Your entrypoint will look the same.
5. **`test_mock.py`**: five tests that show what correct behaviour looks like:
   - `test_good_mock`: a mocked route returns the fake body and `x-mock: true`
   - `test_disabled_mock`: a disabled route returns 500 and `x-mock: true`
   - `test_ignored_mock`: an unlisted route still reaches the real app
   - `test_mock_switch_exact`: only `MOCK=true` turns mocking on
   - `test_fail_fast`: a toml naming a missing function stops at startup

To adapt it to your API, replace the routes in `app.py`, `mock.toml` and `mocked_functions.py`, then change the paths and expected values in `test_mock.py` to match. `serve.py` usually needs no change.

`test_mock.py` is for testing only. Production does not use it. Run it from `python_mock/`:

```sh
uv run --with-requirements requirements.txt test/test_mock.py   # prints "pass" per test, then "ok"
```

`--with-requirements` is needed because the test uses FastAPI, which is listed in `requirements.txt`, not in the project itself. Without it, the run fails with `No module named 'fastapi'`.

Or with pytest, if you already use it: `pytest test/test_mock.py`.

## Upgrading

Change the commit or tag in the install line and reinstall. Pin to a tag for stable builds.
