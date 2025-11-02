# Handbook Backend

Проект разворачивает Flask + SQLAlchemy сервис (`backend_flask/`), работающий с PostgreSQL через Docker Compose. Для удобства поддержки в репозитории также сохранён Node.js каркас (`backend/`), но по умолчанию сервис запускается только на Flask.

## Directory map
- `backend/` - (опционально) Express implementation with TypeScript
- `backend_flask/` - Flask implementation with SQLAlchemy (основной сервис)
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
- `PORT_BACKEND` - API/UI port published to the host (default 3000)
- `PORT_DATABASE` - host port for PostgreSQL (default 5432)
- `DATABASE_URL` - connection string inside containers (`postgresql+psycopg2://postgres:postgres@db:5432/handbook`)
- `SECRET_KEY` - Flask session key

## Running the Flask backend
Build and start the API together with PostgreSQL:
```powershell
docker compose --env-file backend_flask\.env up --build backend_flask db
```
- Service name: `backend_flask`
- Uses `gunicorn` in the container (`backend_flask/Dockerfile`)
- Creates tables through SQLAlchemy models and seeds lookup values in `app/seed.py`
- Endpoints exposed at `http://localhost:${PORT_BACKEND}/api`

To switch between stacks, stop the current profile:
```powershell
docker compose down
```
then bring up the Flask stack again (Node.js service is disabled by default).

## REST API (основные точки)
Base path: `/api`
- `GET /health` — пинг и проверка БД
- `GET /suppliers`, `POST /suppliers`, `PUT /suppliers/<id>`, `DELETE /suppliers/<id>`
- `GET /products`, `POST /products`, `GET /products/<id>`, `PUT /products/<id>`, `DELETE /products/<id>`
- `GET /requests`, `POST /requests` (массовое создание с позициями)
- `GET /products/<id>/competition` — конкурентная карта по товару
- `GET /supplier-prices`, `POST /supplier-prices`, `PUT /supplier-prices/<id>`, `DELETE /supplier-prices/<id>`

Interactive documentation:
- JSON: `http://localhost:${PORT_BACKEND}/api/openapi.json`
- Swagger UI: `http://localhost:${PORT_BACKEND}/api/docs`
- Спецификация: `openapi/openapi.json`

## Web UI
- Доступно по адресу `http://localhost:${PORT_BACKEND}/` сразу после поднятия контейнера.
- Позволяет выполнять CRUD для поставщиков, товаров и записей о ценах, быстрый поиск по таблицам и построение конкурентной карты (таблица предложений поставщиков).
- Работает поверх REST-эндпоинтов, дополнительных прокси не требуется (достаточно пробросить порт `PORT_BACKEND`).
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















