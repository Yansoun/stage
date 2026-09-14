from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.mapping_validation.router import router as mapping_router

app = FastAPI(title="ERP Mapping Validation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mapping_router, prefix="/mapping", tags=["mapping"])