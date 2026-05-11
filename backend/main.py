from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.db.session import engine
from app.models.evaluacion import Base
from app.core.config import settings

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción, especificar los dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la Plataforma de Evaluación Docente IA API v1"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
