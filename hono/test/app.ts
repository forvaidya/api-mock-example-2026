// Same as app.py: the real app. Knows nothing about mocks.
import { Hono } from "hono";

export const app = new Hono();

// c = "context": holds the request and helpers to build a response.
app.get("/foobar", (c) => c.json({ value: Math.floor(Math.random() * 1_000_000) + 1 }));

// not in mock.toml: passes through even when MOCK=true
app.get("/time", (c) => c.json({ now: new Date().toISOString().slice(0, 19) }));

// disabled in mock.toml: works unmocked, refused when MOCK=true
app.post("/sensitive", (c) => c.json({ message: "sensitive done" }));
