from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (registra los modelos en Base.metadata)
from app.database import Base, engine
from app.routers import auth, candidates, votes, voters


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="API Sistema de Votaciones",
    description="API RESTful para gestionar votantes, candidatos y votos con estadisticas.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(voters.router)
app.include_router(candidates.router)
app.include_router(votes.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
