from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    flask_env: str
    secret_key: str
    db_uri: str
    port_backend: int


def load_settings() -> Settings:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    load_dotenv()

    import os

    flask_env = os.getenv("FLASK_ENV", "development")
    secret_key = os.getenv("SECRET_KEY", "change-me")
    port_backend = int(os.getenv("PORT_BACKEND", "3000"))
    db_uri = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@db:5432/handbook",
    )

    return Settings(
        flask_env=flask_env,
        secret_key=secret_key,
        db_uri=db_uri,
        port_backend=port_backend,
    )
