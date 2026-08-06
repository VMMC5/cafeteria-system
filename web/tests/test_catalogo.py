from app.services import api_client

ADMIN_TOKENS = {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}
ADMIN_ME = {
    "id_usuario": 1, "nombre": "Admin", "apellido_paterno": "Sistema",
    "apellido_materno": None, "correo": "admin@cafeteria.com",
    "nombre_usuario": "admin", "id_rol": 1, "activo": True,
    "fecha_registro": "2026-07-04T00:00:00Z",
    "rol": {"id_rol": 1, "nombre_rol": "Administrador", "descripcion": None},
}
CATEGORIAS = [
    {"id_categoria": 1, "nombre_categoria": "Bebidas calientes", "descripcion": None},
    {"id_categoria": 2, "nombre_categoria": "Postres", "descripcion": "Dulces"},
]
# Decimal viaja como string en JSON: los stubs usan strings, no floats.
PRODUCTOS = [
    {"id_producto": 1, "id_categoria": 1, "nombre_producto": "Latte",
     "descripcion": None, "precio_venta": "45.00", "disponible": True,
     "fecha_registro": "2026-07-04T00:00:00Z", "categoria": CATEGORIAS[0]},
    {"id_producto": 2, "id_categoria": 2, "nombre_producto": "Brownie",
     "descripcion": "Con nuez", "precio_venta": "35.50", "disponible": False,
     "fecha_registro": "2026-07-04T00:00:00Z", "categoria": CATEGORIAS[1]},
]


def _login(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    client.post("/login", data={"correo": "admin@cafeteria.com", "password": "secret123"})


def test_catalogo_sin_sesion_redirige_a_login(client):
    r = client.get("/catalogo/productos")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_catalogo_redirige_a_productos(client, monkeypatch):
    _login(client, monkeypatch)
    r = client.get("/catalogo")
    assert r.status_code == 302
    assert "/catalogo/productos" in r.headers["Location"]


def test_lista_productos_renderiza_precio_string(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_productos", lambda a, c=None, d=None: PRODUCTOS)
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    cuerpo = client.get("/catalogo/productos").get_data(as_text=True)
    assert "Latte" in cuerpo
    assert "$ 45.00" in cuerpo
    assert "No disponible" in cuerpo  # Brownie está inactivo


def test_lista_productos_pasa_filtros_a_la_api(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}

    def fake_list(access, id_categoria=None, disponible=None):
        llamado["id_categoria"] = id_categoria
        llamado["disponible"] = disponible
        return []

    monkeypatch.setattr(api_client, "list_productos", fake_list)
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    client.get("/catalogo/productos?categoria=2&disponible=0")
    assert llamado == {"id_categoria": 2, "disponible": False}


def test_crear_producto_ok_redirige(client, monkeypatch):
    _login(client, monkeypatch)
    capturado = {}

    def fake_create(access, payload):
        capturado["payload"] = payload
        return {"id_producto": 9, **payload}

    monkeypatch.setattr(api_client, "create_producto", fake_create)
    r = client.post("/catalogo/productos", data={
        "nombre_producto": "Capuchino", "descripcion": "",
        "id_categoria": "1", "precio_venta": "52.00", "disponible": "on",
    })
    assert r.status_code == 302
    assert "/catalogo/productos" in r.headers["Location"]
    # precio viaja como string tal cual (Pydantic Decimal lo acepta)
    assert capturado["payload"] == {
        "nombre_producto": "Capuchino", "descripcion": None,
        "id_categoria": 1, "precio_venta": "52.00", "disponible": True,
    }


def test_crear_producto_error_api_rerenderiza(client, monkeypatch):
    _login(client, monkeypatch)
    from app.services.api_client import ApiError

    def fake_create(access, payload):
        raise ApiError(422, "precio_venta inválido")

    monkeypatch.setattr(api_client, "create_producto", fake_create)
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    r = client.post("/catalogo/productos", data={
        "nombre_producto": "X", "descripcion": "", "id_categoria": "1",
        "precio_venta": "-1", "disponible": "on",
    })
    assert r.status_code == 422
    assert "inválido" in r.get_data(as_text=True)


def test_form_editar_producto_precarga(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "get_producto", lambda a, i: PRODUCTOS[0])
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    cuerpo = client.get("/catalogo/productos/1/editar").get_data(as_text=True)
    assert 'value="Latte"' in cuerpo
    assert 'value="45.00"' in cuerpo


def test_toggle_producto_manda_negacion(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}

    def fake_update(access, id_producto, payload):
        llamado["id"] = id_producto
        llamado["payload"] = payload
        return {"id_producto": id_producto, **payload}

    monkeypatch.setattr(api_client, "update_producto", fake_update)
    # Brownie está en disponible=False; la lista manda el valor destino "1"
    r = client.post("/catalogo/productos/2/toggle", data={"disponible": "1"})
    assert r.status_code == 302
    assert llamado == {"id": 2, "payload": {"disponible": True}}


def test_sidebar_muestra_catalogo(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_productos", lambda a, c=None, d=None: [])
    monkeypatch.setattr(api_client, "list_categorias", lambda a: [])
    cuerpo = client.get("/catalogo/productos").get_data(as_text=True)
    assert "Catálogo" in cuerpo


def test_lista_categorias_renderiza(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    cuerpo = client.get("/catalogo/categorias").get_data(as_text=True)
    assert "Bebidas calientes" in cuerpo
    assert "Postres" in cuerpo


def test_crear_categoria_ok_redirige(client, monkeypatch):
    _login(client, monkeypatch)
    capturado = {}

    def fake_create(access, payload):
        capturado["payload"] = payload
        return {"id_categoria": 9, **payload}

    monkeypatch.setattr(api_client, "create_categoria", fake_create)
    r = client.post("/catalogo/categorias", data={
        "nombre_categoria": "Ensaladas", "descripcion": "",
    })
    assert r.status_code == 302
    assert capturado["payload"] == {"nombre_categoria": "Ensaladas", "descripcion": None}


def test_crear_categoria_error_api_rerenderiza(client, monkeypatch):
    _login(client, monkeypatch)
    from app.services.api_client import ApiError

    def fake_create(access, payload):
        raise ApiError(409, "La categoría ya existe")

    monkeypatch.setattr(api_client, "create_categoria", fake_create)
    r = client.post("/catalogo/categorias", data={
        "nombre_categoria": "Postres", "descripcion": "",
    })
    assert r.status_code == 409
    assert "ya existe" in r.get_data(as_text=True)


def test_actualizar_categoria_llama_api(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}

    def fake_update(access, id_categoria, payload):
        llamado["id"] = id_categoria
        llamado["payload"] = payload
        return {"id_categoria": id_categoria, **payload}

    monkeypatch.setattr(api_client, "update_categoria", fake_update)
    r = client.post("/catalogo/categorias/2", data={
        "nombre_categoria": "Repostería", "descripcion": "Dulces",
    })
    assert r.status_code == 302
    assert llamado["id"] == 2
    assert llamado["payload"]["nombre_categoria"] == "Repostería"


def test_eliminar_categoria_ok(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}
    monkeypatch.setattr(
        api_client, "delete_categoria",
        lambda a, i: llamado.setdefault("id", i),
    )
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    r = client.post("/catalogo/categorias/2/eliminar", follow_redirects=True)
    assert r.status_code == 200
    assert llamado["id"] == 2
    assert "Categoría eliminada." in r.get_data(as_text=True)


def test_eliminar_categoria_con_productos_flashea_error(client, monkeypatch):
    _login(client, monkeypatch)
    from app.services.api_client import ApiError

    def fake_delete(access, id_categoria):
        raise ApiError(409, "La categoría tiene productos asociados")

    monkeypatch.setattr(api_client, "delete_categoria", fake_delete)
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    r = client.post("/catalogo/categorias/1/eliminar", follow_redirects=True)
    assert r.status_code == 200  # la lista sigue viva
    assert "productos asociados" in r.get_data(as_text=True)


MESAS = [
    {"id_mesa": 1, "numero_mesa": 1, "capacidad": 4, "ubicacion": "Terraza", "estado": "Disponible"},
    {"id_mesa": 2, "numero_mesa": 2, "capacidad": 2, "ubicacion": None, "estado": "Ocupada"},
    {"id_mesa": 3, "numero_mesa": 3, "capacidad": 6, "ubicacion": "Salón", "estado": "Reservada"},
]


def test_lista_mesas_renderiza_estados(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_mesas", lambda a: MESAS)
    cuerpo = client.get("/catalogo/mesas").get_data(as_text=True)
    assert "Terraza" in cuerpo
    assert "Disponible" in cuerpo
    assert "Ocupada" in cuerpo
    assert "Reservada" in cuerpo


def test_crear_mesa_ok_manda_payload_tipado(client, monkeypatch):
    _login(client, monkeypatch)
    capturado = {}

    def fake_create(access, payload):
        capturado["payload"] = payload
        return {"id_mesa": 9, **payload}

    monkeypatch.setattr(api_client, "create_mesa", fake_create)
    r = client.post("/catalogo/mesas", data={
        "numero_mesa": "11", "capacidad": "4", "ubicacion": "", "estado": "Disponible",
    })
    assert r.status_code == 302
    assert capturado["payload"] == {
        "numero_mesa": 11, "capacidad": 4, "ubicacion": None, "estado": "Disponible",
    }


def test_form_mesa_ocupada_no_ofrece_estado(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "get_mesa", lambda a, i: MESAS[1])
    cuerpo = client.get("/catalogo/mesas/2/editar").get_data(as_text=True)
    assert 'name="estado"' not in cuerpo  # sin selector
    assert "Ocupada" in cuerpo  # badge solo-lectura


def test_actualizar_mesa_sin_estado_no_lo_manda(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}

    def fake_update(access, id_mesa, payload):
        llamado["id"] = id_mesa
        llamado["payload"] = payload
        return {"id_mesa": id_mesa, **payload}

    monkeypatch.setattr(api_client, "update_mesa", fake_update)
    # el form de una mesa Ocupada postea sin campo estado
    r = client.post("/catalogo/mesas/2", data={
        "numero_mesa": "2", "capacidad": "4", "ubicacion": "Barra",
    })
    assert r.status_code == 302
    assert llamado["id"] == 2
    assert "estado" not in llamado["payload"]
    assert llamado["payload"]["capacidad"] == 4


def test_eliminar_mesa_referenciada_flashea_error(client, monkeypatch):
    _login(client, monkeypatch)
    from app.services.api_client import ApiError

    def fake_delete(access, id_mesa):
        raise ApiError(409, "La mesa tiene pedidos asociados")

    monkeypatch.setattr(api_client, "delete_mesa", fake_delete)
    monkeypatch.setattr(api_client, "list_mesas", lambda a: MESAS)
    r = client.post("/catalogo/mesas/1/eliminar", follow_redirects=True)
    assert r.status_code == 200
    assert "pedidos asociados" in r.get_data(as_text=True)


def test_eliminar_mesa_ok(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}
    monkeypatch.setattr(api_client, "delete_mesa", lambda a, i: llamado.setdefault("id", i))
    monkeypatch.setattr(api_client, "list_mesas", lambda a: MESAS)
    r = client.post("/catalogo/mesas/1/eliminar", follow_redirects=True)
    assert r.status_code == 200
    assert llamado["id"] == 1
    assert "Mesa eliminada." in r.get_data(as_text=True)
