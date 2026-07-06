from fastapi import APIRouter

from app.api.v1 import (
    auth,
    categorias,
    compras,
    estados,
    gastos,
    insumos,
    mesas,
    metodos_pago,
    pedidos,
    productos,
    proveedores,
    recetas,
    roles,
    unidades,
    usuarios,
    ventas,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(usuarios.router)
api_router.include_router(roles.router)
api_router.include_router(categorias.router)
api_router.include_router(mesas.router)
api_router.include_router(productos.router)
api_router.include_router(recetas.router)
api_router.include_router(pedidos.router)
api_router.include_router(estados.router)
api_router.include_router(ventas.router)
api_router.include_router(metodos_pago.router)
api_router.include_router(gastos.router)
api_router.include_router(insumos.router)
api_router.include_router(unidades.router)
api_router.include_router(proveedores.router)
api_router.include_router(compras.router)
