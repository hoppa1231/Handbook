from flask import Blueprint, jsonify

# Blueprint for types/categories used in dropdowns
bp = Blueprint('types_data', __name__)

# Try to import a Category model if your app has one.
# If not present, a fallback static list will be returned.
try:
    from app.seed import (
            DEFAULT_REQUEST_TYPES,
            DEFAULT_REQUEST_STATUSES,
            DEFAULT_PRODUCT_CATEGORIES,
        )
except Exception:
    print("Could not import default data from seed.py")
    DEFAULT_REQUEST_TYPES = {}
    DEFAULT_REQUEST_STATUSES = {}
    DEFAULT_PRODUCT_CATEGORIES = {}


@bp.route('/api/types', methods=['GET'])
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
    return jsonify(payload), 200