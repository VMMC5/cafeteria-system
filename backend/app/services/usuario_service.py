from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models import Rol, Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate


def get_or_404(db: Session, id_usuario: int) -> Usuario:
    user = db.get(Usuario, id_usuario)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return user


def authenticate(db: Session, correo: str, password: str) -> Usuario | None:
    user = db.execute(
        select(Usuario).where(Usuario.correo == correo)
    ).scalar_one_or_none()
    if user is None or not user.activo:
        return None
    if not verify_password(password, user.contrasena_hash):
        return None
    return user


def _ensure_rol(db: Session, id_rol: int) -> None:
    if db.get(Rol, id_rol) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "El rol especificado no existe"
        )


def _ensure_unico(
    db: Session, correo: str, nombre_usuario: str, exclude_id: int | None = None
) -> None:
    stmt = select(Usuario).where(
        or_(Usuario.correo == correo, Usuario.nombre_usuario == nombre_usuario)
    )
    for u in db.execute(stmt).scalars():
        if exclude_id is not None and u.id_usuario == exclude_id:
            continue
        if u.correo == correo:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "El correo ya está registrado"
            )
        if u.nombre_usuario == nombre_usuario:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "El nombre de usuario ya está registrado"
            )


def create_usuario(db: Session, data: UsuarioCreate) -> Usuario:
    _ensure_rol(db, data.id_rol)
    _ensure_unico(db, data.correo, data.nombre_usuario)
    user = Usuario(
        nombre=data.nombre,
        apellido_paterno=data.apellido_paterno,
        apellido_materno=data.apellido_materno,
        correo=data.correo,
        nombre_usuario=data.nombre_usuario,
        id_rol=data.id_rol,
        contrasena_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_usuario(
    db: Session, id_usuario: int, data: UsuarioUpdate, actor_id: int
) -> Usuario:
    user = get_or_404(db, id_usuario)
    if data.id_rol is not None:
        _ensure_rol(db, data.id_rol)
        # Hardening: el administrador principal (por correo) no puede perder su rol.
        if user.correo == settings.ADMIN_CORREO:
            rol = db.get(Rol, data.id_rol)
            if rol is None or rol.nombre_rol != "Administrador":
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "No se puede cambiar el rol del administrador principal",
                )
    if data.correo is not None or data.nombre_usuario is not None:
        _ensure_unico(
            db,
            data.correo or user.correo,
            data.nombre_usuario or user.nombre_usuario,
            exclude_id=id_usuario,
        )
    if data.activo is False and id_usuario == actor_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "No puedes desactivar tu propia cuenta"
        )

    for campo in (
        "nombre",
        "apellido_paterno",
        "apellido_materno",
        "correo",
        "nombre_usuario",
        "id_rol",
        "activo",
    ):
        valor = getattr(data, campo)
        if valor is not None:
            setattr(user, campo, valor)
    if data.password is not None:
        user.contrasena_hash = hash_password(data.password)

    db.commit()
    db.refresh(user)
    return user


def soft_delete(db: Session, id_usuario: int, actor_id: int) -> Usuario:
    user = get_or_404(db, id_usuario)
    if id_usuario == actor_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "No puedes desactivar tu propia cuenta"
        )
    user.activo = False
    db.commit()
    db.refresh(user)
    return user


def list_usuarios(db: Session, q: str | None = None) -> list[Usuario]:
    stmt = select(Usuario).order_by(Usuario.id_usuario)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Usuario.nombre.ilike(like),
                Usuario.correo.ilike(like),
                Usuario.nombre_usuario.ilike(like),
            )
        )
    return list(db.execute(stmt).scalars())
