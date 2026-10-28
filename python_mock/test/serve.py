# CUSTOMER entrypoint: the only file that joins the customer's app with our framework.
import os
from pathlib import Path

import asgi_mock as mock  # OURS: the framework (installed package)
import uvicorn

import mocked_functions  # CUSTOMER: what mocked routes return
from app import app  # CUSTOMER: the real app, no mock code

HERE = Path(__file__).resolve().parent

asgi = mock.wrap(app, mocked_functions, toml=HERE / "mock.toml")

if __name__ == "__main__":
    print(f"MOCK={mock.enabled()}", flush=True)
    uvicorn.run(asgi, host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
