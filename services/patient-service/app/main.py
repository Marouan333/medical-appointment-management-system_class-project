from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import patients

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Patient Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "patient-service"}
