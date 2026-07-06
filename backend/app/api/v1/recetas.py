from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.receta import RecetaLineaCreate, RecetaLineaOut
from app.services import receta_service

router = APIRouter(prefix="/productos", tags=["recetas"])


@router.get("/{id_producto}/receta", response_model=list[RecetaLineaOut])
def listar(
    id_producto: int,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return receta_service.listar_receta(db, id_producto, current)


@router.post(
    "/{id_producto}/receta",
    response_model=RecetaLineaOut,
    status_code=status.HTTP_201_CREATED,
)
def agregar(
    id_producto: int,
    data: RecetaLineaCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return receta_service.agregar_linea(db, id_producto, data, current)


@router.delete(
    "/{id_producto}/receta/{id_producto_insumo}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar(
    id_producto: int,
    id_producto_insumo: int,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    receta_service.eliminar_linea(db, id_producto, id_producto_insumo, current)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
