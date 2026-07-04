from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(title="Cafetería API", version="0.1.0")
app.include_router(api_router)


@app.get("/health", tags=["infra"])
def health():
    """Smoke test del entorno (Sprint 0)."""
    return {"status": "ok", "service": "cafeteria-api"}
