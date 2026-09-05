from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.clinical import router as clinical_router
from app.api.consultations import router as consultations_router
from app.api.notes import router as notes_router
from app.api.patients import router as patients_router
from app.api.safety import router as safety_router
from app.api.transcription import router as transcription_router
from app.core.config import settings

app = FastAPI(
    title="MediScribe API",
    description="AI Medical Scribe Documentation Assistant Backend & AIML Pipeline",
    version="1.0.0",
)

# Parse CORS origins
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if not origins:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Canonical /api Routers
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(consultations_router)
app.include_router(transcription_router)
app.include_router(clinical_router)
app.include_router(notes_router)
app.include_router(safety_router)



@app.get("/")
def root():
    return {
        "message": "MediScribe API is running",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.environment,
    }