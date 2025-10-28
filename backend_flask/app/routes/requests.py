from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from flask import jsonify, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from ..database import db
from ..models import Request, RequestItem
from . import api_bp


def serialize_request_item(item: RequestItem) -> Dict[str, Any]:
    return {
        "id": item.id,
        "partNumber": item.part_number,
        "name": item.name,
        "quantity": item.quantity,
        "unit": item.unit,
        "brand": item.brand,
        "model": item.model,
        "serialNumber": item.serial_number,
        "scheme": item.scheme,
        "posScheme": item.pos_scheme,
        "material": item.material,
        "comment": item.comment,
        "unitPrice": item.unit_price,
        "totalPrice": item.total_price,
        "requestId": item.request_id,
        "productId": item.product_id,
    }


def serialize_request(req: Request) -> Dict[str, Any]:
    return {
        "id": req.id,
        "idRequest": req.id_request,
        "typeRequest": req.type_request,
        "typeDescription": req.type.description if req.type else None,
        "datetimeComing": req.datetime_coming.isoformat(),
        "datetimeDelivery": req.datetime_delivery.isoformat() if req.datetime_delivery else None,
        "status": req.status,
        "statusDescription": req.status_rel.description if req.status_rel else None,
        "totalPrice": req.total_price,
        "items": [serialize_request_item(item) for item in req.items],
    }


@api_bp.get("/requests")
def list_requests():
    requests = (
        Request.query.order_by(Request.datetime_coming.desc())
        .options(joinedload(Request.items), joinedload(Request.type), joinedload(Request.status_rel))
        .all()
    )
    return jsonify([serialize_request(req) for req in requests])


def parse_iso_datetime(value: str, field_name: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - simple parsing guard
        raise ValueError(f'Field "{field_name}" must be a valid ISO string') from exc


@api_bp.post("/requests")
def create_request():
    payload = request.get_json(silent=True) or {}

    id_request = payload.get("idRequest")
    datetime_coming = payload.get("datetimeComing")

    if id_request is None or not isinstance(id_request, int):
        return jsonify({"message": 'Field "idRequest" must be an integer'}), 400

    if not datetime_coming or not isinstance(datetime_coming, str):
        return jsonify({"message": 'Field "datetimeComing" must be an ISO string'}), 400

    try:
        parsed_coming = parse_iso_datetime(datetime_coming, "datetimeComing")
        parsed_delivery = (
            parse_iso_datetime(payload["datetimeDelivery"], "datetimeDelivery")
            if payload.get("datetimeDelivery")
            else None
        )
    except ValueError as err:
        return jsonify({"message": str(err)}), 400

    request_model = Request(
        id_request=id_request,
        type_request=payload.get("typeRequest"),
        datetime_coming=parsed_coming,
        datetime_delivery=parsed_delivery,
        status=payload.get("status"),
        total_price=payload.get("totalPrice"),
    )

    items_payload: List[Dict[str, Any]] = payload.get("items") or []

    for item_data in items_payload:
        name = item_data.get("name")
        if not name:
            return jsonify({"message": 'Each request item must include "name"'}), 400

        part_number_raw = item_data.get("partNumber")
        if part_number_raw in (None, ""):
            part_number_value = None
        elif isinstance(part_number_raw, (int, float)):
            part_number_value = str(part_number_raw).strip()
        elif isinstance(part_number_raw, str):
            part_number_value = part_number_raw.strip() or None
        else:
            return jsonify({"message": 'Field "partNumber" must be a string or number if provided'}), 400

        serial_raw = item_data.get("serialNumber")
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

        item_model = RequestItem(
            part_number=part_number_value,
            name=name,
            quantity=item_data.get("quantity"),
            unit=item_data.get("unit"),
            brand=item_data.get("brand"),
            model=item_data.get("model"),
            serial_number=serial_value,
            scheme=item_data.get("scheme"),
            pos_scheme=item_data.get("posScheme"),
            material=item_data.get("material"),
            comment=item_data.get("comment"),
            unit_price=item_data.get("unitPrice"),
            total_price=item_data.get("totalPrice"),
            product_id=item_data.get("productId"),
        )
        request_model.items.append(item_model)

    db.session.add(request_model)

    try:
        db.session.commit()
    except IntegrityError as err:
        db.session.rollback()
        return jsonify({"message": str(err)}), 400

    return jsonify(serialize_request(request_model)), 201
