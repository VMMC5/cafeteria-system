from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.orm import Session

from app.core import deps
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.models import Rol, Usuario
from app.schemas.auth import RefreshRequest, Token
from app.schemas.usuario import UsuarioOut
from app.services import usuario_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _emitir_tokens(db: Session, user: Usuario) -> Token:
    rol = db.get(Rol, user.id_rol)
    return Token(
        access_token=create_access_token(str(user.id_usuario), rol.nombre_rol),
        refresh_token=create_refresh_token(str(user.id_usuario)),
    )


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = usuario_service.authenticate(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos"
        )
    return _emitir_tokens(db, user)


@router.post("/refresh", response_model=Token)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    creds_exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token inválido")
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise creds_exc
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise creds_exc
    user = db.get(Usuario, user_id)
    if user is None or not user.activo:
        raise creds_exc
    return _emitir_tokens(db, user)


@router.get("/me", response_model=UsuarioOut)
def me(current: Usuario = Depends(deps.get_current_user)):
    return current
