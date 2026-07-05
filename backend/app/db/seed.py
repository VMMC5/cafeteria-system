"""Seed de catálogos base (Sprint 0). Idempotente: no duplica filas existentes.

Ejecutar:  docker compose exec api python -m app.db.seed
"""

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Categoria,
    CategoriaGasto,
    Configuracion,
    EstadoPedido,
    Mesa,
    MetodoPago,
    Producto,
    Rol,
    UnidadMedida,
    Usuario,
)

SEED = [
    (
        Rol,
        "nombre_rol",
        [
            {"nombre_rol": "Administrador", "descripcion": "Acceso total al sistema"},
            {"nombre_rol": "Cajero", "descripcion": "Cobro de pedidos y gastos"},
            {"nombre_rol": "Cocinero", "descripcion": "Preparación e inventario"},
            {"nombre_rol": "Mesero", "descripcion": "Toma de pedidos"},
        ],
    ),
    (
        EstadoPedido,
        "nombre_estado",
        [
            {"nombre_estado": "Pendiente"},
            {"nombre_estado": "En preparación"},
            {"nombre_estado": "Listo"},
            {"nombre_estado": "Entregado"},
            {"nombre_estado": "Cancelado"},
        ],
    ),
    (
        MetodoPago,
        "nombre_metodo",
        [
            {"nombre_metodo": "Efectivo"},
            {"nombre_metodo": "Tarjeta"},
            {"nombre_metodo": "Transferencia"},
            {"nombre_metodo": "Otro"},
        ],
    ),
    (
        Categoria,
        "nombre_categoria",
        [
            {"nombre_categoria": "Bebidas"},
            {"nombre_categoria": "Comidas"},
            {"nombre_categoria": "Postres"},
        ],
    ),
    (
        UnidadMedida,
        "nombre_unidad",
        [
            {"nombre_unidad": "Gramo", "abreviatura": "g"},
            {"nombre_unidad": "Kilogramo", "abreviatura": "kg"},
            {"nombre_unidad": "Mililitro", "abreviatura": "ml"},
            {"nombre_unidad": "Litro", "abreviatura": "L"},
            {"nombre_unidad": "Pieza", "abreviatura": "pza"},
        ],
    ),
    (
        CategoriaGasto,
        "nombre_categoria",
        [
            {"nombre_categoria": "Servicios"},
            {"nombre_categoria": "Nómina"},
            {"nombre_categoria": "Mantenimiento"},
        ],
    ),
    (
        Configuracion,
        "clave",
        [
            {
                "clave": "iva_tasa",
                "valor": "0.16",
                "descripcion": "Tasa de IVA (fracción)",
            },
        ],
    ),
]


MESAS_DEMO = [
    {"numero_mesa": n, "capacidad": cap, "ubicacion": ubic, "estado": "Disponible"}
    for n, cap, ubic in [
        (1, 2, "Interior"),
        (2, 2, "Interior"),
        (3, 4, "Interior"),
        (4, 4, "Interior"),
        (5, 4, "Terraza"),
        (6, 6, "Terraza"),
        (7, 6, "Terraza"),
        (8, 8, "Salón"),
        (9, 4, "Salón"),
        (10, 2, "Barra"),
    ]
]

PRODUCTOS_DEMO = [
    ("Bebidas", "Café Americano", "Café negro", 30.0),
    ("Bebidas", "Capuchino", "Con espuma de leche", 42.0),
    ("Bebidas", "Jugo de Naranja", "Natural", 38.0),
    ("Comidas", "Sándwich de Jamón", "Con queso", 65.0),
    ("Comidas", "Ensalada César", "Con pollo", 85.0),
    ("Postres", "Pastel de Chocolate", "Rebanada", 55.0),
    ("Postres", "Flan Napolitano", "Casero", 45.0),
]


def seed_catalogo(db) -> int:
    """Siembra mesas y productos demo. Idempotente."""
    total = 0
    for m in MESAS_DEMO:
        existe = db.query(Mesa).filter(Mesa.numero_mesa == m["numero_mesa"]).first()
        if not existe:
            db.add(Mesa(**m))
            total += 1
    for cat_nombre, nombre, desc, precio in PRODUCTOS_DEMO:
        existe = db.query(Producto).filter(Producto.nombre_producto == nombre).first()
        if existe:
            continue
        cat = db.query(Categoria).filter(Categoria.nombre_categoria == cat_nombre).one()
        db.add(
            Producto(
                id_categoria=cat.id_categoria,
                nombre_producto=nombre,
                descripcion=desc,
                precio_venta=precio,
                disponible=True,
            )
        )
        total += 1
    db.flush()
    return total


def seed_admin(db) -> int:
    """Crea el Administrador inicial desde .env si no existe. Idempotente."""
    existe = db.query(Usuario).filter(Usuario.correo == settings.ADMIN_CORREO).first()
    if existe:
        return 0
    admin_rol = db.query(Rol).filter(Rol.nombre_rol == "Administrador").one()
    db.add(
        Usuario(
            nombre=settings.ADMIN_NOMBRE,
            apellido_paterno="Sistema",
            apellido_materno=None,
            correo=settings.ADMIN_CORREO,
            nombre_usuario="admin",
            contrasena_hash=hash_password(settings.ADMIN_PASSWORD),
            id_rol=admin_rol.id_rol,
        )
    )
    db.flush()
    return 1


def run():
    db = SessionLocal()
    try:
        total = 0
        for model, key, rows in SEED:
            for row in rows:
                existe = (
                    db.query(model).filter(getattr(model, key) == row[key]).first()
                )
                if not existe:
                    db.add(model(**row))
                    total += 1
        total += seed_admin(db)
        total += seed_catalogo(db)
        db.commit()
        print(f"Seed completado: {total} filas nuevas insertadas.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
