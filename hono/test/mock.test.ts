// CUSTOMER tests (same as python_mock/test/test_mock.py): good, disabled and ignored mock, exact switch, fail-fast.
import { expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as mock from "../mock"; // OURS
import * as mockedFunctions from "./mocked_functions";
import { app } from "./app";

function call(mockOn: boolean, method: string, path: string) {
  process.env.MOCK = mockOn ? "true" : "false";
  return mock.wrap(app, mockedFunctions, join(import.meta.dir, "mock.toml")).fetch(new Request(`http://local${path}`, { method }));
}

test("good mock: foobar real unmocked, mocked handler when MOCK=true", async () => {
  let r = await call(false, "GET", "/foobar");
  expect(r.headers.get("x-mock")).toBeNull();
  expect(typeof (await r.json()).value).toBe("number");
  r = await call(true, "GET", "/foobar");
  expect(await r.json()).toEqual({ value: 42 });
  expect(r.headers.get("x-mock")).toBe("true");
});

test("disabled mock: sensitive works unmocked, 500 when MOCK=true", async () => {
  let r = await call(false, "POST", "/sensitive");
  expect(r.status).toBe(200);
  expect(await r.json()).toEqual({ message: "sensitive done" });
  r = await call(true, "POST", "/sensitive");
  expect(r.status).toBe(500);
  expect((await r.json()).error).toContain("disabled");
  expect(r.headers.get("x-mock")).toBe("true");
});

test("ignored mock: time is real in both modes", async () => {
  for (const mockOn of [false, true]) {
    const r = await call(mockOn, "GET", "/time");
    expect((await r.json()).now).toBeDefined();
    expect(r.headers.get("x-mock")).toBeNull();
  }
});

test("only exact 'true' mocks (case-sensitive)", () => {
  for (const v of ["True", "TRUE", "1", "yes", " true"]) {
    process.env.MOCK = v;
    expect(mock.enabled()).toBe(false);
  }
});

test("fail fast: unknown handler stops startup", () => {
  const bad = join(mkdtempSync(join(tmpdir(), "mock-")), "bad.toml");
  writeFileSync(bad, '[[route]]\npath = "/x"\nhandler = "nope"\n');
  expect(() => mock.mockFetch(app, mockedFunctions, bad)).toThrow("nope");
});
