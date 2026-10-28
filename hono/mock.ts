// Same as mock.py: the generic mock framework. Wraps any app that has a `fetch` function.
// The wrapped app needs no code change. Two things are external, passed in by the caller:
//   toml      -> which routes: `handler = "<name>"` (mocked) or `disabled = true` (500); unlisted pass through
//   functions -> what mocked routes return: a module with one exported function per handler, f(req) -> JSON body
import { readFileSync } from "node:fs";

// Python's ASGI callable becomes a web-standard `fetch`: Request in, Response out.
type Fetch = (req: Request) => Response | Promise<Response>;

// `?` = optional field, like r.get("method", "GET") in Python.
type Route = { method?: string; path: string; handler?: string; disabled?: boolean; status?: number };

// a functions module, its exports looked up by name like getattr(functions, name) in Python
type Functions = Record<string, unknown>;

const MOCK_FILE = process.env.MOCK_FILE ?? "mock.toml";

export function enabled(): boolean {
  return process.env.MOCK === "true"; // exactly "true", case-sensitive; anything else is real
}

// ponytail: re-reads toml per request so edits apply live; cache it if latency matters
function routes(path: string, functions: Functions): Map<string, Route> {
  const toml = Bun.TOML.parse(readFileSync(path, "utf8")) as { route?: Route[] };
  // Key is "GET /foobar" (a string), the Python version used a ("GET", "/foobar") tuple.
  const map = new Map((toml.route ?? []).map((r) => [`${(r.method ?? "GET").toUpperCase()} ${r.path}`, r]));
  for (const [key, r] of map) {
    if (r.disabled) continue; // disabled: never touches functions, so nothing to check
    if (typeof functions[r.handler ?? ""] !== "function") {
      throw new Error(`${path} ${key}: handler ${JSON.stringify(r.handler)} not found in functions module`);
    }
  }
  return map;
}

export function mockFetch(app: { fetch: Fetch }, functions: Functions, path = MOCK_FILE): Fetch {
  routes(path, functions); // fail fast: bad mock.toml or unknown handler stops startup
  return async (req) => {
    const where = `${req.method} ${new URL(req.url).pathname}`;
    const route = routes(path, functions).get(where);
    if (!route) return app.fetch(req); // not listed: forward to the real app

    if (route.disabled) {
      // disabled in mock mode: refuse, never call the real handler
      return Response.json({ error: `${where} is disabled in mock mode` }, { status: 500, headers: { "x-mock": "true" } });
    }
    // mocked: per-route behavior lives in the functions module
    const data = await (functions[route.handler!] as (req: Request) => unknown)(req);
    return Response.json(data, { status: route.status ?? 200, headers: { "x-mock": "true" } });
  };
}

export function wrap(app: { fetch: Fetch }, functions: Functions, path = MOCK_FILE): { fetch: Fetch } {
  return enabled() ? { fetch: mockFetch(app, functions, path) } : app;
}
