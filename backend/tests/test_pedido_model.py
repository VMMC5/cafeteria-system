from decimal import Decimal


def test_pedido_total_suma_subtotales(db, admin):
    from app.models import (
        Categoria,
        DetallePedido,
        EstadoPedido,
        Mesa,
        Pedido,
        Producto,
    )

    cat = db.query(Categoria).first()
    prod = Producto(
        id_categoria=cat.id_categoria,
        nombre_producto="X",
        precio_venta=10,
        disponible=True,
    )
    mesa = Mesa(numero_mesa=555, capacidad=4)
    db.add_all([prod, mesa])
    db.flush()
    estado = (
        db.query(EstadoPedido).filter(EstadoPedido.nombre_estado == "Pendiente").one()
    )
    pedido = Pedido(
        id_mesa=mesa.id_mesa,
        id_usuario=admin.id_usuario,
        id_estado=estado.id_estado,
        detalle=[
            DetallePedido(id_producto=prod.id_producto, cantidad=2, precio_unitario=10),
            DetallePedido(id_producto=prod.id_producto, cantidad=1, precio_unitario=10),
        ],
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    assert pedido.total == Decimal("30.00")
    assert pedido.detalle[0].producto.nombre_producto == "X"
