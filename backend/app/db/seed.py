"""Seed de catálogos base (Sprint 0). Idempotente: no duplica filas existentes.

Ejecutar:  docker compose exec api python -m app.db.seed
"""

from app.db.session import SessionLocal
from app.models import (
    Categoria,
    CategoriaGasto,
    EstadoPedido,
    MetodoPago,
    Rol,
    UnidadMedida,
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
]


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
        db.commit()
        print(f"Seed completado: {total} filas nuevas insertadas.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
