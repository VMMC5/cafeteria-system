from fastapi import FastAPI

app = FastAPI(title="Cafetería API", version="0.1.0")


@app.get("/health", tags=["infra"])
def health():
    """Smoke test del entorno (Sprint 0)."""
    return {"status": "ok", "service": "cafeteria-api"}
