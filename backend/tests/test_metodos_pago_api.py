def test_metodos_lista(client, admin_headers):
    r = client.get("/api/v1/metodos_pago", headers=admin_headers)
    assert r.status_code == 200
    nombres = [m["nombre_metodo"] for m in r.json()]
    assert len(r.json()) == 4
    assert "Efectivo" in nombres


def test_metodos_sin_token_401(client):
    assert client.get("/api/v1/metodos_pago").status_code == 401
