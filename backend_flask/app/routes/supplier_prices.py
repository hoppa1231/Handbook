from __future__ import annotations

from datetime import timedelta

from flask import jsonify, request

from ..database import db
from ..models import SupplierProductPrice, Supplier, Product
from . import api_bp


def serialize_price(price: SupplierProductPrice) -> dict:
    lead_days = None
    if price.lead_time is not None:
        lead_days = price.lead_time.days + price.lead_time.seconds / 86400

    return {
        "id": price.id,
        "productId": price.product_id,
        "supplierId": price.supplier_id,
        "totalPrice": price.total_price,
        "leadTimeDays": lead_days,
        "currency": price.cy,
    }


def parse_lead_time(days_value):
    if days_value in (None, ""):
        return None
    try:
        days_float = float(days_value)
    except (TypeError, ValueError):
        raise ValueError('Field "leadTimeDays" must be a number if provided')
    return timedelta(days=days_float)


@api_bp.get("/supplier-prices")
def list_supplier_prices():
    query = SupplierProductPrice.query

    product_id = request.args.get("productId", type=int)
    supplier_id = request.args.get("supplierId", type=int)

    if product_id is not None:
        query = query.filter(SupplierProductPrice.product_id == product_id)
    if supplier_id is not None:
        query = query.filter(SupplierProductPrice.supplier_id == supplier_id)

    prices = query.order_by(SupplierProductPrice.id.desc()).all()
    return jsonify([serialize_price(price) for price in prices])


@api_bp.post("/supplier-prices")
def create_supplier_price():
    payload = request.get_json(silent=True) or {}

    product_id = payload.get("productId")
    supplier_id = payload.get("supplierId")

    if not isinstance(product_id, int):
        return jsonify({"message": 'Field "productId" must be an integer'}), 400
    if not isinstance(supplier_id, int):
        return jsonify({"message": 'Field "supplierId" must be an integer'}), 400

    if not Product.query.get(product_id):
        return jsonify({"message": f"Product {product_id} not found"}), 404
    if not Supplier.query.get(supplier_id):
        return jsonify({"message": f"Supplier {supplier_id} not found"}), 404

    lead_time = None
    if "leadTimeDays" in payload:
        try:
            lead_time = parse_lead_time(payload.get("leadTimeDays"))
        except ValueError as exc:
            return jsonify({"message": str(exc)}), 400

    price = SupplierProductPrice(
        product_id=product_id,
        supplier_id=supplier_id,
        total_price=payload.get("totalPrice"),
        lead_time=lead_time,
        cy=payload.get("currency"),
    )

    db.session.add(price)
    db.session.commit()
    return jsonify(serialize_price(price)), 201


@api_bp.put("/supplier-prices/<int:price_id>")
def update_supplier_price(price_id: int):
    payload = request.get_json(silent=True) or {}
    price = SupplierProductPrice.query.get_or_404(price_id)

    if "totalPrice" in payload:
        total_price = payload.get("totalPrice")
        if total_price in (None, ""):
            price.total_price = None
        else:
            try:
                price.total_price = float(total_price)
            except (TypeError, ValueError):
                return jsonify({"message": 'Field "totalPrice" must be a number'}), 400

    if "leadTimeDays" in payload:
        try:
            price.lead_time = parse_lead_time(payload.get("leadTimeDays"))
        except ValueError as exc:
            return jsonify({"message": str(exc)}), 400

    if "currency" in payload:
        price.cy = payload.get("currency")

    db.session.commit()
    return jsonify(serialize_price(price))


@api_bp.delete("/supplier-prices/<int:price_id>")
def delete_supplier_price(price_id: int):
    price = SupplierProductPrice.query.get_or_404(price_id)
    db.session.delete(price)
    db.session.commit()
    return ("", 204)
