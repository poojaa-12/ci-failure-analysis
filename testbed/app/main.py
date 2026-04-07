from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/compute")
def compute(x: int):
    return {"result": x * 2}
