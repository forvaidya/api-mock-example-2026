# Main Rule

Always use bun, own local deps (`node_modules/` in this folder) and maintain `package.json` + `bun.lock` with versions anchored (exact, no `^`/`~`).
Add deps only with `bun add --exact <pkg>`.

# Key takeaway

**The server starts in exactly one place: `Bun.serve` in `serve.ts`.** `app.ts` is only setup (routes), so importing it starts nothing.
`serve.ts` is the only file that joins app + mock: `const server = mock.wrap(app, mockedFunctions)` then `Bun.serve({ fetch: server.fetch })`.
Python counterpart: `uvicorn.run` in `../serve.py`.

# Objective
prototype to use mock api response from the same Interface based on an env var MOCK=true.
Mirror of the FastAPI prototype (`../mock.md`) for comparison.

## workings
A Hono server with an endpoint /foobar which returns a random number. (main behavior)
Mock - Must return a fixed number configurable using toml.

The wrapper must need no code change in the app. Any mock behavior is changed from toml. Mock invocation happens based on env var: `MOCK=true bun serve.ts`.

# Tech Stack
Hono on Bun (TypeScript run directly, built-in TOML parser and test runner).

# Outcome
should be mock and unmock with variable change

## Extended outcome - want to apply this for real apis


# Implementation

| File | Python equivalent | Role |
|------|-------------------|------|
| `mock.ts` | `../python_mock/src/asgi_mock/` | **OURS**: the framework. Generic wrapper around any `{ fetch }` app; never edited by customers. |
| `test/app.ts` | `../python_mock/test/app.py` | CUSTOMER: real Hono app: `/foobar`, `/time`, `POST /sensitive`. Knows nothing about mocks. |
| `test/serve.ts` | `../python_mock/test/serve.py` | CUSTOMER: their server, `mock.wrap(app, mockedFunctions, tomlPath)` + `Bun.serve`. |
| `test/mock.toml` | `../python_mock/test/mock.toml` | CUSTOMER: `handler` (mocked) or `disabled = true` (500). Unlisted routes pass through. |
| `test/mocked_functions.ts` | `../python_mock/test/mocked_functions.py` | CUSTOMER: one exported function per `handler`. Unknown handler fails at startup. |
| `test/mock.test.ts` | `../python_mock/test/test_mock.py` | CUSTOMER: good / disabled / ignored mock, exact switch, fail-fast. |

## Setup
```sh
bun install
```
Adding a dep: `bun add --exact <pkg>` (updates `package.json` + `bun.lock`).

## Run
```sh
bun test/serve.ts               # real   → {"value": <random>}
MOCK=true bun test/serve.ts     # mocked → {"value": 42}
PORT=8766 bun test/serve.ts     # port 8000 is taken by OrbStack on this machine
bun test                        # 5 pass
```

## Applying to real APIs
Any Hono app (or anything exposing `fetch(Request) → Response`) gets mocking by wrapping it once at the entrypoint: `const server = mock.wrap(app, mockedFunctions)`, then list the endpoints to fake in `mock.toml`. Unlisted endpoints stay real, so you can mock one route at a time.

Not yet supported (add when needed): path params / query matching, per-request dynamic values, mocking *outbound* calls your app makes to a third-party API (that needs a `fetch` interceptor, not this wrapper).
