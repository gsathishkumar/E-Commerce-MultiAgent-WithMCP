from fastapi import APIRouter
from app.api.routes import ingestion, files, retrieval
 
api_router = APIRouter()
 
api_router.include_router(ingestion.router, tags=["Ingestion"])
api_router.include_router(files.router, tags=["Files"])
api_router.include_router(retrieval.router, tags=["Retrieval"])