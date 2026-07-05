from fastapi import APIRouter

from app.api.v1 import auth, categorias, roles, usuarios

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(usuarios.router)
api_router.include_router(roles.router)
api_router.include_router(categorias.router)
