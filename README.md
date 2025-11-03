# Handbook Backend

This repository deploys the Flask + SQLAlchemy service (`backend_flask/`) backed by PostgreSQL via Docker Compose. A Node.js skeleton (`backend/`) is kept for reference, but the default runtime is Flask.

## Directory map

- `backend/` — optional Express + TypeScript skeleton
- `backend_flask/` — primary Flask + SQLAlchemy service with admin UI
- `docker-compose.yml` — Compose configuration for Flask API and PostgreSQL
- `README.md` — project guide

## Shared database

- PostgreSQL 15 (service `db`)
- Tables and seed data are created automatically on startup
- Inspect data with `docker compose exec db psql -U postgres -d handbook`
- Reset everything: `docker compose down -v`

## Environment files

```powershell
copy backend_flask\.env.example backend_flask\.env
```

Important keys:

- `PORT_BACKEND` — exposed API/UI port (default 3000)
- `PORT_DATABASE` — exposed PostgreSQL port (default 5432)
- `DATABASE_URL` — container connection string (`postgresql+psycopg2://postgres:postgres@db:5432/handbook`)
- `SECRET_KEY` — Flask secret key

## Running the Flask backend

```powershell
docker compose --env-file backend_flask\.env up --build backend_flask db
```

- API: `http://localhost:${PORT_BACKEND}/api`
- UI: `http://localhost:${PORT_BACKEND}/`
- Stop services: `docker compose down`

## REST API (highlights)

Base path: `/api`

- `GET /health` — health check
- `GET/POST/PUT/DELETE /suppliers`
- `GET/POST/PUT/DELETE /products`
- `GET /products/<id>` — product details
- `GET /products/<id>/competition` — supplier offers for a product
- `GET/POST/PUT/DELETE /supplier-prices`
- `GET/POST /requests`
- `GET /types` — reference data (categories, statuses, request types)

OpenAPI docs:

- JSON: `http://localhost:${PORT_BACKEND}/api/openapi.json`
- Swagger UI: `http://localhost:${PORT_BACKEND}/api/docs`

## Web UI

- Served at `http://localhost:${PORT_BACKEND}/`
- Tabs for suppliers, products, competition map, supplier prices
- CRUD with inline delete buttons, instant search, category dropdowns pulled from `/api/types`
- Uses the same REST endpoints, no extra proxy setup is required (just expose `PORT_BACKEND`)

## Importing data from Excel

- Place `ITOG 03.12.24.xlsx` next to `scripts/import_excel.py`
- Run the importer (override host/port if running outside Docker):
  ```powershell
  python scripts\import_excel.py --excel "ИТОГ 03.12.24.xlsx" --host localhost --port 5432
  ```
- The script adjusts schema (varchar columns), creates missing suppliers/products, and upserts supplier prices

## Next ideas

1. Introduce Alembic migrations
2. Extend UI with request management and advanced filters
3. Add authentication and role-based access control
