from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.patients import router as patients_router
from app.api.consultations import router as consultations_router

app = FastAPI(
    title="MediScribe API",
    version="1.0.0"
)
app.include_router(patients_router)
app.include_router(consultations_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "MediScribe API is running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }