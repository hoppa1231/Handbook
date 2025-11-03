from flask import jsonify, request

from . import api_bp

from app.seed import (
        DEFAULT_REQUEST_TYPES,
        DEFAULT_REQUEST_STATUSES,
        DEFAULT_PRODUCT_CATEGORIES,
    )


@api_bp.get("/types")
def get_types():
    """
    Возвращает список типов (категорий) для выпадающего списка.
    Формат: [{ "id": <id>, "name": "<display name>" }, ...]
    """
    def _map_dict(d):
        return [{"id": k, "name": v} for k, v in d.items()]

    payload = {
        "request_types": _map_dict(DEFAULT_REQUEST_TYPES),
        "request_statuses": _map_dict(DEFAULT_REQUEST_STATUSES),
        "product_categories": _map_dict(DEFAULT_PRODUCT_CATEGORIES),
    }
    return jsonify(payload)