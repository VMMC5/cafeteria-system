# Sistema Integral de Gestión para Cafetería

Sistema móvil y web para automatizar pedidos, inventario, ventas y gastos de una cafetería.

**Stack:** FastAPI (API) · Flask (Web Admin) · React Native + Expo (Móvil) · PostgreSQL · Docker Compose

## Estructura

```
cafeteria-system/
├── backend/   # API · Python + FastAPI
├── mobile/    # App móvil · React Native + Expo
├── web/       # Panel Admin · Flask
├── docs/      # Requerimientos, diccionario de datos, diagramas
└── docker-compose.yml
```

## Arranque rápido

```bash
cp .env.example .env              # ajustar secretos
docker compose up -d --build      # levanta db + api + web + adminer
```

Las dependencias del panel web viven en la imagen (se instalan en el
`Dockerfile`), no en el volumen montado: tras un `git pull` que las cambie,
un `docker compose up -d` sin `--build` reutiliza la imagen vieja y el panel
no arranca. Usa siempre `--build` al levantar tras actualizar el repo.

El stack tampoco aplica migraciones al arrancar: tras un `git pull` que
traiga una revisión Alembic nueva, hay que correrla a mano antes (o después)
del seed.

```bash
docker compose exec api alembic upgrade head   # esquema al día (migraciones)
docker compose exec api python -m app.db.seed  # catálogos + admin + demo
```

- API docs → http://localhost:8000/docs
- Web admin → http://localhost:5000
- Adminer (BD) → http://localhost:8080

La app móvil no va en Docker: `cd mobile && npx expo start`.

## Convención de ramas

- `main` — siempre estable y desplegable.
- `feature/<modulo>-<descripcion>` — ej. `feature/api-auth`.
- PRs con revisión de al menos 1 compañero antes de mergear.
