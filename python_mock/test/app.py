import random
from datetime import datetime

from fastapi import FastAPI

app = FastAPI()


@app.get("/foobar")
def foobar():
    return {"value": random.randint(1, 1_000_000)}


@app.get("/time")  # not in mock.toml: passes through even when MOCK=true
def time():
    return {"now": datetime.now().isoformat(timespec="seconds")}


@app.post("/sensitive")  # disabled in mock.toml: works unmocked, refused when MOCK=true
def sensitive():
    return {"message": "sensitive done"}
