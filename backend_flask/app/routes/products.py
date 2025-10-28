from flask import jsonify, request

from sqlalchemy.orm import joinedload

from ..database import db
from ..models import Product, ProductCategory
from . import api_bp


def serialize_product(product: Product) -> dict:
    category_description = product.category_rel.description if product.category_rel else None

    return {
        "id": product.id,
        "partNumber": product.part_number,
        "name": product.name,
        "brand": product.brand,
        "model": product.model,
        "serialNumber": product.serial_number,
        "scheme": product.scheme,
        "posScheme": product.pos_scheme,
        "material": product.material,
        "size": product.size,
        "comment": product.comment,
        "category": product.category,
        "categoryDescription": category_description,
    }


@api_bp.get("/products")
def list_products():
    products = (
        Product.query.order_by(Product.id.desc())
        .options(joinedload(Product.category_rel))
        .all()
    )
    return jsonify([serialize_product(product) for product in products])


@api_bp.post("/products")
def create_product():
    payload = request.get_json(silent=True) or {}

    part_number = payload.get("partNumber")
    name = payload.get("name")

    if part_number is None:
        return jsonify({"message": 'Field "partNumber" is required'}), 400

    if isinstance(part_number, (int, float)):
        part_number_value = str(part_number).strip()
    elif isinstance(part_number, str):
        part_number_value = part_number.strip()
    else:
        return jsonify({"message": 'Field "partNumber" must be a string or number'}), 400

    if not part_number_value:
        return jsonify({"message": 'Field "partNumber" is required'}), 400

    if not name:
        return jsonify({"message": 'Field "name" is required'}), 400

    category_code = payload.get("category")
    if category_code:
        exists = db.session.query(
            db.exists().where(ProductCategory.code == category_code)
        ).scalar()
        if not exists:
            return (
                jsonify(
                    {
                        "message": f'Category "{category_code}" does not exist. Seed it first or use another code.'
                    }
                ),
                400,
            )

    serial_raw = payload.get("serialNumber")
    serial_value = None
    if serial_raw not in (None, ""):
        if isinstance(serial_raw, (int, float)):
            serial_value = int(serial_raw)
        elif isinstance(serial_raw, str):
            serial_raw = serial_raw.strip()
            if serial_raw:
                try:
                    serial_value = int(serial_raw)
                except ValueError:
                    return jsonify({"message": 'Field "serialNumber" must be an integer if provided'}), 400
        else:
            return jsonify({"message": 'Field "serialNumber" must be an integer if provided'}), 400

    product = Product(
        part_number=part_number_value,
        name=name,
        brand=payload.get("brand"),
        model=payload.get("model"),
        serial_number=serial_value,
        scheme=payload.get("scheme"),
        pos_scheme=payload.get("posScheme"),
        material=payload.get("material"),
        size=payload.get("size"),
        comment=payload.get("comment"),
        category=category_code,
    )

    db.session.add(product)
    db.session.commit()

    return jsonify(serialize_product(product)), 201
