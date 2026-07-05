from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.venta import VentaCreate, VentaOut
from app.services import venta_service

router = APIRouter(prefix="/ventas", tags=["ventas"])


@router.post("", response_model=VentaOut, status_code=status.HTTP_201_CREATED)
def cobrar(
    data: VentaCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    venta = venta_service.cobrar(db, data, current)
    return venta_service.to_out(db, venta)


@router.get("/{id_venta}", response_model=VentaOut)
def detalle(
    id_venta: int,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return venta_service.to_out(db, venta_service.get_or_404(db, id_venta))
