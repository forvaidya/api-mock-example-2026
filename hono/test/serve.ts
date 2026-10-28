// CUSTOMER entrypoint: the only file that joins the customer's app with our framework.
import { join } from "node:path";
import * as mock from "../mock"; // OURS: the framework
import * as mockedFunctions from "./mocked_functions"; // CUSTOMER: what mocked routes return
import { app } from "./app"; // CUSTOMER: the real app, no mock code

const server = mock.wrap(app, mockedFunctions, join(import.meta.dir, "mock.toml"));

Bun.serve({ hostname: "127.0.0.1", port: Number(process.env.PORT ?? 8000), fetch: server.fetch });
console.log(`listening on 127.0.0.1:${process.env.PORT ?? 8000} MOCK=${mock.enabled()}`);
