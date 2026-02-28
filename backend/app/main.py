from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, init_extensions
from app.models import contracts  # noqa: F401 — register models with Base
from app.models import decisions  # noqa: F401 — register models with Base
from app.modules.contracts.router import router as contracts_router
from app.modules.chat.router import router as chat_router
from app.modules.decisions.router import router as decisions_router

# Enable required extensions and create all tables on startup
init_extensions()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Contract Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contracts_router, prefix="/api/v1/contracts", tags=["contracts"])
app.include_router(decisions_router, prefix="/api/v1/decisions", tags=["decisions"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
