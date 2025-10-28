from flask import jsonify, request

from ..database import db
from ..models import Supplier
from . import api_bp


def serialize_supplier(supplier: Supplier) -> dict:
    return {
        "id": supplier.id,
        "name": supplier.name,
        "address": supplier.address,
        "contact": supplier.contact,
        "website": supplier.website,
        "rating": supplier.rating,
    }


@api_bp.get("/suppliers")
def list_suppliers():
    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()
    return jsonify([serialize_supplier(supplier) for supplier in suppliers])


@api_bp.post("/suppliers")
def create_supplier():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")

    if not name:
        return jsonify({"message": 'Field "name" is required'}), 400

    supplier = Supplier(
        name=name,
        address=payload.get("address"),
        contact=payload.get("contact"),
        website=payload.get("website"),
        rating=payload.get("rating"),
    )

    db.session.add(supplier)
    db.session.commit()

    return jsonify(serialize_supplier(supplier)), 201
