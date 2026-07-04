from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models import Rol, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

_CREDS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise _CREDS_EXC
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise _CREDS_EXC
    user = db.get(Usuario, user_id)
    if user is None or not user.activo:
        raise _CREDS_EXC
    return user


def require_admin(
    current: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
) -> Usuario:
    rol = db.get(Rol, current.id_rol)
    if rol is None or rol.nombre_rol != "Administrador":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requiere rol Administrador")
    return current
