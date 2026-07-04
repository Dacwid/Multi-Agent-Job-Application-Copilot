from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import resumes

app = FastAPI(title="ApplyPilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resumes.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
