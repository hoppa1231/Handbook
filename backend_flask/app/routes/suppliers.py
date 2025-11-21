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
        "nomenclature": supplier.nomenclature,
        "counterpartyType": supplier.counterparty_type,
        "techAudit": supplier.tech_audit,
        "finAudit": supplier.fin_audit,
        "workExperience": supplier.work_experience,
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

    def pick_value(*keys):
        for key in keys:
            if key in payload:
                return payload[key]
        return None

    supplier = Supplier(
        name=name,
        address=payload.get("address"),
        contact=payload.get("contact"),
        website=payload.get("website"),
        rating=payload.get("rating"),
        nomenclature=payload.get("nomenclature"),
        counterparty_type=pick_value("counterpartyType", "counterparty_type"),
        tech_audit=pick_value("techAudit", "tech_audit"),
        fin_audit=pick_value("finAudit", "fin_audit"),
        work_experience=pick_value("workExperience", "work_experience"),
    )

    db.session.add(supplier)
    db.session.commit()

    return jsonify(serialize_supplier(supplier)), 201


@api_bp.put("/suppliers/<int:supplier_id>")
def update_supplier(supplier_id: int):
    payload = request.get_json(silent=True) or {}
    supplier = Supplier.query.get_or_404(supplier_id)

    name = payload.get("name")
    if name is not None:
        if not name:
            return jsonify({"message": 'Field "name" cannot be empty'}), 400
        supplier.name = name

    field_mapping = {
        "address": "address",
        "contact": "contact",
        "website": "website",
        "rating": "rating",
        "nomenclature": "nomenclature",
        "counterpartyType": "counterparty_type",
        "counterparty_type": "counterparty_type",
        "techAudit": "tech_audit",
        "tech_audit": "tech_audit",
        "finAudit": "fin_audit",
        "fin_audit": "fin_audit",
        "workExperience": "work_experience",
        "work_experience": "work_experience",
    }

    for key, model_field in field_mapping.items():
        if key in payload:
            setattr(supplier, model_field, payload[key])

    db.session.commit()
    return jsonify(serialize_supplier(supplier))


@api_bp.delete("/suppliers/<int:supplier_id>")
def delete_supplier(supplier_id: int):
    supplier = Supplier.query.get_or_404(supplier_id)
    db.session.delete(supplier)
    db.session.commit()
    return ("", 204)
