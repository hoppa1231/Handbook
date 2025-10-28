#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

import pandas as pd
import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Column indices in the Excel sheet (zero-based)
COL_INDEXES = {
    "direction": 1,
    "brand": 2,
    "part_number": 3,
    "name": 4,
    "product": 5,
    "product_number": 6,
    "material": 7,
    "size": 8,
    "scheme": 9,
    "position": 10,
    "comment": 11,
}

SUPPLIER_GROUP_START = 12
SUPPLIER_GROUP_WIDTH = 3  # supplier name, price, lead time


@dataclass(slots=True)
class SupplierColumn:
    name: str
    price_idx: int
    lead_idx: int


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
    # Final fallback to process-level environment
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


def read_excel(path: Path) -> Tuple[pd.Series, pd.Series, pd.DataFrame]:
    """Return supplier row, header row, and data frame with product rows."""
    df = pd.read_excel(path, header=None)
    if df.shape[0] < 4:
        raise ValueError("Excel sheet does not contain the expected header rows.")

    supplier_row = df.iloc[1]
    header_row = df.iloc[2]
    data = df.iloc[3:].copy()
    data.columns = header_row
    data.reset_index(drop=True, inplace=True)
    data = data.dropna(how="all")
    return supplier_row, header_row, data


def extract_suppliers(supplier_row: pd.Series, header_row: pd.Series) -> List[SupplierColumn]:
    suppliers: List[SupplierColumn] = []
    for idx in range(SUPPLIER_GROUP_START, len(header_row), SUPPLIER_GROUP_WIDTH):
        header_value = header_row.iloc[idx]
        supplier_name = supplier_row.iloc[idx]
        if not isinstance(header_value, str):
            continue
        if not header_value.startswith("П") and not header_value.startswith("P"):
            # Expect "ПОСТАВЩИК" or similar; skip unrelated columns
            continue
        if isinstance(supplier_name, float) or pd.isna(supplier_name):
            continue
        supplier_name = str(supplier_name).strip()
        if not supplier_name:
            continue

        price_idx = idx + 1
        lead_idx = idx + 2
        suppliers.append(SupplierColumn(name=supplier_name, price_idx=price_idx, lead_idx=lead_idx))
    return suppliers


def value_or_none(row: Iterable, index: int) -> Optional[str]:
    try:
        value = row[index]
    except IndexError:
        return None
    if pd.isna(value):
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return str(value)


def parse_price(raw: object) -> Optional[float]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    if not text:
        return None
    text = text.replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_lead_time(raw: object) -> Optional[str]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    text = str(raw).strip()
    if not text:
        return None
    lower = text.lower().replace("cays", "days")
    digits = re.findall(r"\d+", lower)
    if not digits:
        return None
    number = digits[-1]
    if "week" in lower:
        return f"{number} weeks"
    return f"{number} days"


def normalize_part_number(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def get_supplier_id(cur, cache: Dict[str, int], name: str) -> int:
    if name in cache:
        return cache[name]

    cur.execute("select id from suppliers where name = %s", (name,))
    row = cur.fetchone()
    if row:
        cache[name] = row[0]
        return row[0]

    cur.execute(
        "insert into suppliers (name) values (%s) returning id",
        (name,),
    )
    supplier_id = cur.fetchone()[0]
    cache[name] = supplier_id
    return supplier_id


def get_product_id(cur, cache: Dict[Tuple[str, str, Optional[str]], int], product: Dict[str, Optional[str]]) -> Optional[int]:
    part_number = normalize_part_number(product["part_number"])
    name = product["name"]
    brand = product["brand"]

    if not part_number or not name:
        return None

    key = (part_number, name, brand)
    if key in cache:
        return cache[key]

    cur.execute(
        """
        select id from products
        where part_number::text = %s
          and name = %s
          and coalesce(brand, '') = coalesce(%s, '')
        """,
        (part_number, name, brand),
    )
    row = cur.fetchone()
    if row:
        product_id = row[0]
        cache[key] = product_id
        return product_id

    try:
        cur.execute(
            """
            insert into products (
              part_number, name, brand, model, serial_number,
              scheme, pos_scheme, material, size, comment, category
            )
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            returning id
            """,
            (
                part_number,
                name,
                brand,
                product["model"],
                product["serial_number"],
                product["scheme"],
                product["pos_scheme"],
                product["material"],
                product["size"],
                product["comment"],
                product["category"],
            ),
        )
    except psycopg2.Error as exc:
        detail = {
            "part_number": part_number,
            "name": name,
            "brand": brand,
            "model": product["model"],
            "serial_number": product["serial_number"],
            "scheme": product["scheme"],
            "pos_scheme": product["pos_scheme"],
            "material": product["material"],
            "size": product["size"],
            "comment": product["comment"],
            "category": product["category"],
        }
        print("Failed to insert product with data:", detail, file=sys.stderr)
        raise exc
    product_id = cur.fetchone()[0]
    cache[key] = product_id
    return product_id


def serial_as_int(raw: Optional[str]) -> Optional[int]:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def build_product(row: List[object]) -> Dict[str, Optional[str]]:
    product = {
        "direction": value_or_none(row, COL_INDEXES["direction"]),
        "brand": value_or_none(row, COL_INDEXES["brand"]),
        "part_number": value_or_none(row, COL_INDEXES["part_number"]),
        "name": value_or_none(row, COL_INDEXES["name"]),
        "product": value_or_none(row, COL_INDEXES["product"]),
        "product_number": value_or_none(row, COL_INDEXES["product_number"]),
        "material": value_or_none(row, COL_INDEXES["material"]),
        "size": value_or_none(row, COL_INDEXES["size"]),
        "scheme": value_or_none(row, COL_INDEXES["scheme"]),
        "pos_scheme": value_or_none(row, COL_INDEXES["position"]),
        "comment": value_or_none(row, COL_INDEXES["comment"]),
        "category": None,
        "model": value_or_none(row, COL_INDEXES["product"]),
        "serial_number": value_or_none(row, COL_INDEXES["product_number"]),
    }
    product["part_number"] = normalize_part_number(product["part_number"])
    return product


def ensure_schema(conn: PgConnection) -> None:
    statements = [
        """
        alter table if exists products
        alter column part_number type varchar(100)
        using part_number::text,
        alter column pos_scheme type varchar(100)
        using pos_scheme::text
        """,
        """
        alter table if exists request_items
        alter column part_number type varchar(100)
        using part_number::text,
        alter column pos_scheme type varchar(100)
        using pos_scheme::text
        """
    ]
    cur = conn.cursor()
    for stmt in statements:
        try:
            cur.execute(stmt)
            conn.commit()
        except psycopg2.Error:
            conn.rollback()
    cur.close()


def import_data(conn: PgConnection, data: pd.DataFrame, suppliers: List[SupplierColumn]) -> Tuple[int, int]:
    cur = conn.cursor()
    supplier_cache: Dict[str, int] = {}
    product_cache: Dict[Tuple[str, str, Optional[str]], int] = {}

    price_map: Dict[Tuple[int, int], Tuple[Optional[float], Optional[str]]] = {}
    products_processed = 0

    for idx, row in data.iterrows():
        row_values = row.tolist()
        product = build_product(row_values)

        if not product["name"]:
            continue
        part_number = product["part_number"]
        if not part_number:
            # Skip rows without part number to keep DB constraints consistent
            continue
        product["serial_number"] = serial_as_int(product["serial_number"])

        product_id = get_product_id(cur, product_cache, product)
        if product_id is None:
            continue
        products_processed += 1

        for supplier in suppliers:
            price = parse_price(row_values[supplier.price_idx]) if supplier.price_idx < len(row_values) else None
            lead_time = parse_lead_time(row_values[supplier.lead_idx]) if supplier.lead_idx < len(row_values) else None
            if price is None and lead_time is None:
                continue

            supplier_id = get_supplier_id(cur, supplier_cache, supplier.name)
            key = (product_id, supplier_id)
            current_price, current_lead = price_map.get(key, (None, None))
            new_price = price if price is not None else current_price
            new_lead = lead_time if lead_time is not None else current_lead
            price_map[key] = (new_price, new_lead)

    price_rows = [
        (product_id, supplier_id, values[0], values[1])
        for (product_id, supplier_id), values in price_map.items()
    ]

    if price_rows:
        execute_values(
            cur,
            """
            insert into supplier_product_prices (
              product_id, supplier_id, total_price, lead_time, cy
            )
            values %s
            on conflict (product_id, supplier_id)
            do update set
              total_price = excluded.total_price,
              lead_time = coalesce(excluded.lead_time, supplier_product_prices.lead_time),
              cy = excluded.cy
            """,
            [(p_id, s_id, price, lead, None) for p_id, s_id, price, lead in price_rows],
        )

    conn.commit()
    cur.close()
    return products_processed, len(price_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import suppliers, products, and prices from Excel.")
    parser.add_argument("--excel", required=True, type=Path, help="Path to the Excel file to import.")
    parser.add_argument(
        "--env",
        type=Path,
        help="Optional path to .env file containing DATABASE_URL (defaults to backend/.env or backend_flask/.env).",
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Override the database host (useful outside Docker, e.g. 'localhost').",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Override the database port.",
    )
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

    supplier_row, header_row, data = read_excel(args.excel)
    suppliers = extract_suppliers(supplier_row, header_row)
    if not suppliers:
        print("No suppliers found in the Excel header.", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(prepared_url)
    try:
        ensure_schema(conn)
        products_count, price_count = import_data(conn, data, suppliers)
        print(f"Processed {products_count} product rows and upserted {price_count} supplier price entries.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
