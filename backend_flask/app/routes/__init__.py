from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

from . import health, suppliers, products, requests, docs, supplier_prices, types  # noqa: E402,F401
