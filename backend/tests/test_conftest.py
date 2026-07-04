def test_client_health(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_admin_headers_funcionan(client, admin_headers):
    assert "Authorization" in admin_headers
    assert admin_headers["Authorization"].startswith("Bearer ")
