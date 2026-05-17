from fastapi import APIRouter
from app.api.v1.endpoints import evaluacion, auth, docentes, etl_v2

api_router = APIRouter()
api_router.include_router(auth.router,       prefix="/auth",      tags=["auth"])
api_router.include_router(evaluacion.router, prefix="/evaluacion", tags=["evaluacion"])
api_router.include_router(docentes.router,   prefix="/docentes",  tags=["docentes"])
api_router.include_router(etl_v2.router,     prefix="/etl",       tags=["etl"])
