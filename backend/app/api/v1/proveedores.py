from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.compra import ProveedorCreate, ProveedorOut
from app.services import compra_service

router = APIRouter(prefix="/proveedores", tags=["proveedores"])


@router.get("", response_model=list[ProveedorOut])
def listar(
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return compra_service.listar_proveedores(db, current)


@router.post("", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: ProveedorCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return compra_service.crear_proveedor(db, data, current)
