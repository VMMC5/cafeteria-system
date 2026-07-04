from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Rol, Usuario
from app.schemas.rol import RolOut

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RolOut])
def listar(db: Session = Depends(get_db), _: Usuario = Depends(deps.require_admin)):
    return list(db.execute(select(Rol).order_by(Rol.id_rol)).scalars())
