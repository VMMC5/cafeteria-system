import requests

from app.config import Config

TIMEOUT = 10


class ApiError(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


def _base():
    return Config.API_BASE_URL


def _detail(resp):
    try:
        body = resp.json()
    except ValueError:
        return resp.text or f"Error {resp.status_code}"
    d = body.get("detail", body) if isinstance(body, dict) else body
    if isinstance(d, list):
        return "; ".join(str(x.get("msg", x)) for x in d)
    return str(d)


def _headers(access):
    return {"Authorization": f"Bearer {access}"}


def _check(resp, ok=200):
    if resp.status_code >= 400 or (ok is not None and resp.status_code != ok):
        raise ApiError(resp.status_code, _detail(resp))
    return resp.json()


def login(correo, password):
    r = requests.post(
        f"{_base()}/auth/login",
        data={"username": correo, "password": password},
        timeout=TIMEOUT,
    )
    return _check(r)


def refresh(refresh_token):
    r = requests.post(
        f"{_base()}/auth/refresh",
        json={"refresh_token": refresh_token},
        timeout=TIMEOUT,
    )
    return _check(r)


def get_me(access):
    r = requests.get(f"{_base()}/auth/me", headers=_headers(access), timeout=TIMEOUT)
    return _check(r)


def list_usuarios(access, q=None):
    params = {"q": q} if q else None
    r = requests.get(
        f"{_base()}/usuarios", headers=_headers(access), params=params, timeout=TIMEOUT
    )
    return _check(r)


def get_usuario(access, id_usuario):
    r = requests.get(
        f"{_base()}/usuarios/{id_usuario}", headers=_headers(access), timeout=TIMEOUT
    )
    return _check(r)


def create_usuario(access, payload):
    r = requests.post(
        f"{_base()}/usuarios", headers=_headers(access), json=payload, timeout=TIMEOUT
    )
    return _check(r, ok=None)


def update_usuario(access, id_usuario, payload):
    r = requests.patch(
        f"{_base()}/usuarios/{id_usuario}",
        headers=_headers(access),
        json=payload,
        timeout=TIMEOUT,
    )
    return _check(r, ok=None)


def delete_usuario(access, id_usuario):
    r = requests.delete(
        f"{_base()}/usuarios/{id_usuario}", headers=_headers(access), timeout=TIMEOUT
    )
    return _check(r, ok=None)


def list_roles(access):
    r = requests.get(f"{_base()}/roles", headers=_headers(access), timeout=TIMEOUT)
    return _check(r)


def get_reporte_resumen(access, desde=None, hasta=None):
    r = requests.get(
        f"{_base()}/reportes/resumen",
        headers=_headers(access),
        params={"desde": desde, "hasta": hasta},
        timeout=TIMEOUT,
    )
    return _check(r)


def get_ventas_por_dia(access, desde=None, hasta=None):
    r = requests.get(
        f"{_base()}/reportes/ventas-por-dia",
        headers=_headers(access),
        params={"desde": desde, "hasta": hasta},
        timeout=TIMEOUT,
    )
    return _check(r)


def get_top_productos(access, desde=None, hasta=None, limite=10):
    r = requests.get(
        f"{_base()}/reportes/top-productos",
        headers=_headers(access),
        params={"desde": desde, "hasta": hasta, "limite": limite},
        timeout=TIMEOUT,
    )
    return _check(r)
