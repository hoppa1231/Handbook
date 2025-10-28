# Handbook Backends

Two interchangeable backends share one PostgreSQL database and API contract:
1. **Node.js + Express + TypeScript** (`backend/`)
2. **Flask + SQLAlchemy** (`backend_flask/`)

Both variants expose the same `/api` endpoints and rely on Docker Compose for local orchestration.

## Directory map
- `backend/` - Express implementation with TypeScript
- `backend_flask/` - Flask implementation with SQLAlchemy
- `docker-compose.yml` - services for both backends and PostgreSQL
- `README.md` - this guide

## Shared database
- PostgreSQL 15 runs in the `db` service.
- Tables, foreign keys and lookup data match the schema you described (suppliers, products, requests, etc.).
- Healthcheck (`pg_isready`) keeps the backend services from starting before Postgres is ready.

Resetting the database (removes tables and data):
```powershell
docker compose down -v
```

To inspect the data:
```powershell
docker compose exec db psql -U postgres -d handbook
```

## Environment files
Copy the examples before starting a backend:
```powershell
copy backend\.env.example backend\.env
copy backend_flask\.env.example backend_flask\.env
```

Important keys (use the same values in both files):
- `PORT_BACKEND` - API port published to the host (default 3000)
- `PORT_DATABASE` - host port for PostgreSQL (default 5432)
- `DATABASE_URL` - connection string inside containers
- `SECRET_KEY` (Flask only) - Flask session key

## Running the Node.js backend (default)
```powershell
docker compose --env-file backend\.env up --build
```
- Service name: `backend`
- Auto-reloads with `ts-node-dev`
- Initializes schema and lookup data at startup (`backend/src/db/schema.ts`)
- Healthcheck: `http://localhost:${PORT_BACKEND}/api/health`

Manual type-check:
```powershell
docker compose exec backend npm run build
```

## Running the Flask backend
The Flask service lives in a separate Compose profile so it does not collide with the Node service on the same port.

```powershell
docker compose --profile flask --env-file backend_flask\.env up --build backend_flask db
```
- Service name: `backend_flask`
- Uses `gunicorn` in the container (`backend_flask/Dockerfile`)
- Creates tables through SQLAlchemy models and seeds lookup values in `app/seed.py`
- Endpoints mirror the Node implementation

To switch between stacks, stop the current profile:
```powershell
docker compose down
```
then bring up the desired variant (Node or Flask).

## REST API (shared contract)
Base path: `/api`
- `GET /health` - pings database
- `GET /suppliers`, `POST /suppliers`
- `GET /products`, `POST /products`
- `GET /requests`, `POST /requests` (accepts optional `items` array and stores request + positions in a single transaction)

Interactive documentation is served from the shared OpenAPI definition:
- JSON: `http://localhost:${PORT_BACKEND}/api/openapi.json`
- Swagger UI: `http://localhost:${PORT_BACKEND}/api/docs`
- Specification lives in `openapi/openapi.json`; edit once and both stacks pick it up automatically.
## Importing data from Excel
- Place the workbook (for example, `ИТОГ 03.12.24.xlsx`) in the project directory or pass an absolute path.
- Run the importer; it reads `DATABASE_URL` from `.env` automatically:
  ```powershell
  python scripts\import_excel.py --excel "ИТОГ 03.12.24.xlsx"
  ```
- Optional: add `--env path\to\.env` to target a specific environment file.
- When running outside Docker, override the host/port so the DSN resolves locally:
  ```powershell
  python scripts\import_excel.py --excel "ИТОГ 03.12.24.xlsx" --host localhost --port 5432
  ```

The script creates missing suppliers/products and upserts supplier prices (including lead times) in PostgreSQL. It relies on the Python packages `pandas`, `openpyxl`, `psycopg2-binary`, and `python-dotenv`—install them via `python -m pip install pandas openpyxl psycopg2-binary python-dotenv` if they are not available.

Example payload for creating a request:
```json
{
  "idRequest": 101,
  "typeRequest": "exam",
  "datetimeComing": "2025-10-25T12:00:00.000Z",
  "status": "new",
  "totalPrice": 5000,
  "items": [
    {
      "name": "Filter",
      "quantity": 2,
      "unitPrice": 2500,
      "totalPrice": 5000
    }
  ]
}
```

## Next ideas
1. Add proper migrations (Prisma/Knex for Node, Alembic for Flask) instead of auto-creating tables.
2. Extend API with update/delete endpoints and supplier price management.
3. Add validation (zod/express-validator or marshmallow/pydantic) and automated tests for both stacks.
