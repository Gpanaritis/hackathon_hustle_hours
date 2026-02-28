from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, init_extensions
from app.modules.contracts.router import router as contracts_router
from app.modules.chat.router import router as chat_router

# Enable required extensions and create all tables on startup
init_extensions()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Contract Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contracts_router, prefix="/api/v1/contracts", tags=["contracts"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
