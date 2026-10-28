// Same as mocked_functions.py: per-route mock behavior.
// One exported function per mocked route, named by `handler` in mock.toml.
// Each receives the Request and returns the JSON body.
// mock.ts checks at startup that every `handler` in mock.toml exists here, so a typo fails fast.

export function foobar(_req: Request) {
  return { value: 42 };
}
