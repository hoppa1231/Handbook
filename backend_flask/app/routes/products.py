from flask import jsonify, request

from sqlalchemy.orm import joinedload

from ..database import db
from ..models import Product, ProductCategory, SupplierProductPrice, Supplier
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


@api_bp.put("/products/<int:product_id>")
def update_product(product_id: int):
    payload = request.get_json(silent=True) or {}
    product = Product.query.get_or_404(product_id)

    if "partNumber" in payload:
        part_number = payload.get("partNumber")
        if isinstance(part_number, (int, float)):
            part_number_value = str(part_number).strip()
        elif isinstance(part_number, str):
            part_number_value = part_number.strip()
        else:
            return jsonify({"message": 'Field "partNumber" must be a string or number'}), 400

        if not part_number_value:
            return jsonify({"message": 'Field "partNumber" is required'}), 400
        product.part_number = part_number_value

    if "name" in payload:
        if not payload["name"]:
            return jsonify({"message": 'Field "name" cannot be empty'}), 400
        product.name = payload["name"]

    if "serialNumber" in payload:
        serial_raw = payload.get("serialNumber")
        if serial_raw in (None, ""):
            product.serial_number = None
        elif isinstance(serial_raw, (int, float)):
            product.serial_number = int(serial_raw)
        elif isinstance(serial_raw, str):
            serial_raw = serial_raw.strip()
            if serial_raw:
                try:
                    product.serial_number = int(serial_raw)
                except ValueError:
                    return jsonify({"message": 'Field "serialNumber" must be an integer if provided'}), 400
            else:
                product.serial_number = None
        else:
            return jsonify({"message": 'Field "serialNumber" must be an integer if provided'}), 400

    if "category" in payload:
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
        product.category = category_code or None

    for field, key in (
        ("brand", "brand"),
        ("model", "model"),
        ("scheme", "scheme"),
        ("pos_scheme", "posScheme"),
        ("material", "material"),
        ("size", "size"),
        ("comment", "comment"),
    ):
        if key in payload:
            setattr(product, field, payload[key])

    db.session.commit()
    return jsonify(serialize_product(product))


@api_bp.delete("/products/<int:product_id>")
def delete_product(product_id: int):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return ("", 204)


@api_bp.get("/products/<int:product_id>")
def get_product(product_id: int):
    product = (
        Product.query.options(joinedload(Product.category_rel))
        .filter(Product.id == product_id)
        .first_or_404()
    )
    return jsonify(serialize_product(product))


@api_bp.get("/products/<int:product_id>/competition")
def product_competition(product_id: int):
    product = Product.query.get_or_404(product_id)
    offers = (
        SupplierProductPrice.query.filter_by(product_id=product.id)
        .join(SupplierProductPrice.supplier)
        .order_by(Supplier.name.asc())
        .all()
    )
    result = []
    for offer in offers:
        if offer.lead_time is not None:
            lead_days = offer.lead_time.days + offer.lead_time.seconds / 86400
            lead_time_value = lead_days
        else:
            lead_time_value = None
        result.append(
            {
                "supplierId": offer.supplier_id,
                "supplierName": offer.supplier.name if offer.supplier else None,
                "totalPrice": offer.total_price,
                "leadTimeDays": lead_time_value,
                "currency": offer.cy,
            }
        )
    return jsonify({"product": serialize_product(product), "offers": result})
