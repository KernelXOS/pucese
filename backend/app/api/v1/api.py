from fastapi import APIRouter
from app.api.v1.endpoints import evaluacion, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(evaluacion.router, prefix="/evaluacion", tags=["evaluacion"])
