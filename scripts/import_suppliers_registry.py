#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse, urlunparse

import pandas as pd
import psycopg2
from psycopg2.extensions import connection as PgConnection
from dotenv import load_dotenv


SOURCE_COLUMNS = {
    "Наименование": "name",
    "Контакты": "contact",
    "Номенклатура": "nomenclature",
    "Тип контрагента": "counterparty_type",
    "Тех. Аудит": "tech_audit",
    "Фин. Аудит": "fin_audit",
    "опыт работы": "work_experience",
}


@dataclass()
class SupplierRecord:
    name: str
    contact: Optional[str] = None
    nomenclature: Optional[str] = None
    counterparty_type: Optional[str] = None
    tech_audit: Optional[str] = None
    fin_audit: Optional[str] = None
    work_experience: Optional[str] = None


def load_environment(explicit_env: Optional[Path]) -> None:
    """Load environment variables from .env files."""
    candidates: List[Path] = []
    if explicit_env:
        candidates.append(explicit_env)
    candidates.extend([Path("backend/.env"), Path("backend_flask/.env")])

    loaded_any = False
    for candidate in candidates:
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            loaded_any = True
    if not loaded_any:
        load_dotenv(override=False)


def normalise_connection_url(url: str) -> str:
    """Adjust SQLAlchemy-style URLs to psycopg2-compatible DSNs."""
    if "+psycopg2" in url:
        return url.replace("+psycopg2", "")
    return url


def prepare_connection_url(url: str, host_override: Optional[str], port_override: Optional[int]) -> str:
    cleaned = normalise_connection_url(url)
    parsed = urlparse(cleaned)

    scheme = parsed.scheme
    path = parsed.path or ""
    query = parsed.query or ""
    username = parsed.username or ""
    password = parsed.password or ""
    host = parsed.hostname or ""
    port = parsed.port

    if host_override:
        host = host_override
    elif host == "db":
        host = "127.0.0.1"

    if port_override is not None:
        port = port_override

    netloc = ""
    if username:
        netloc += username
        if password:
            netloc += f":{password}"
        netloc += "@"
    netloc += host
    if port:
        netloc += f":{port}"

    return urlunparse((scheme, netloc, path, "", query, ""))


def mask_connection_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme
    path = parsed.path or ""
    query = parsed.query or ""
    username = parsed.username or ""
    password = parsed.password
    host = parsed.hostname or ""
    port = parsed.port

    netloc = ""
    if username:
        netloc += username
        if password:
            netloc += ":***"
        netloc += "@"
    netloc += host
    if port:
        netloc += f":{port}"

    return urlunparse((scheme, netloc, path, "", query, ""))


def clean_cell(value: object) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text if text else None


def read_registry(path: Path) -> List[SupplierRecord]:
    df = pd.read_excel(path)
    missing = [column for column in SOURCE_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {', '.join(missing)}")

    aggregated: Dict[str, SupplierRecord] = {}
    for _, row in df.iterrows():
        raw_name = clean_cell(row["Наименование"])
        if not raw_name:
            continue
        key = raw_name.lower()
        record = aggregated.get(key) or SupplierRecord(name=raw_name)

        for src, dest in SOURCE_COLUMNS.items():
            value = clean_cell(row[src])
            if value and getattr(record, dest) is None:
                setattr(record, dest, value)

        aggregated[key] = record

    return list(aggregated.values())


def ensure_schema(conn: PgConnection) -> None:
    statement = """
        alter table if exists suppliers
        add column if not exists nomenclature text,
        add column if not exists counterparty_type text,
        add column if not exists tech_audit text,
        add column if not exists fin_audit text,
        add column if not exists work_experience text
    """
    cur = conn.cursor()
    try:
        cur.execute(statement)
        conn.commit()
    except psycopg2.Error as exc:
        conn.rollback()
        raise exc
    finally:
        cur.close()


def upsert_suppliers(conn: PgConnection, suppliers: Iterable[SupplierRecord]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    cur = conn.cursor()
    for supplier in suppliers:
        cur.execute(
            "select id from suppliers where lower(name) = lower(%s) limit 1",
            (supplier.name,),
        )
        row = cur.fetchone()

        if row is None:
            cur.execute(
                """
                insert into suppliers (
                  name, contact, nomenclature, counterparty_type, tech_audit, fin_audit, work_experience
                )
                values (%s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    supplier.name,
                    supplier.contact,
                    supplier.nomenclature,
                    supplier.counterparty_type,
                    supplier.tech_audit,
                    supplier.fin_audit,
                    supplier.work_experience,
                ),
            )
            inserted += 1
            continue

        supplier_id = row[0]
        updates: Dict[str, Optional[str]] = {
            "contact": supplier.contact,
            "nomenclature": supplier.nomenclature,
            "counterparty_type": supplier.counterparty_type,
            "tech_audit": supplier.tech_audit,
            "fin_audit": supplier.fin_audit,
            "work_experience": supplier.work_experience,
        }
        updates = {k: v for k, v in updates.items() if v is not None}
        if not updates:
            continue

        set_clause = ", ".join(f"{col} = %s" for col in updates.keys())
        cur.execute(
            f"update suppliers set {set_clause} where id = %s",
            [*updates.values(), supplier_id],
        )
        updated += 1

    conn.commit()
    cur.close()
    return inserted, updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Import suppliers from registry Excel file.")
    parser.add_argument("--excel", required=True, type=Path, help="Path to the Реестр поставщиков Excel file.")
    parser.add_argument(
        "--env",
        type=Path,
        help="Optional path to .env file containing DATABASE_URL (defaults to backend/.env or backend_flask/.env).",
    )
    parser.add_argument("--host", type=str, help="Override database host (useful outside Docker).")
    parser.add_argument("--port", type=int, help="Override database port.")
    args = parser.parse_args()

    if not args.excel.is_file():
        print(f"Excel file '{args.excel}' does not exist.", file=sys.stderr)
        sys.exit(1)

    load_environment(args.env)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not defined in environment variables.", file=sys.stderr)
        sys.exit(1)

    prepared_url = prepare_connection_url(database_url, args.host, args.port)
    print(f"Using DATABASE_URL: {mask_connection_url(prepared_url)}")

    try:
        suppliers = read_registry(args.excel)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    if not suppliers:
        print("No supplier rows found in the registry.", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(prepared_url)
    try:
        ensure_schema(conn)
        inserted, updated = upsert_suppliers(conn, suppliers)
        print(f"Imported {len(suppliers)} suppliers from Excel: {inserted} inserted, {updated} updated.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
