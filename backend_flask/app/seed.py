from __future__ import annotations

from flask import current_app

from .database import db
from .models import ProductCategory, RequestStatus, RequestType


DEFAULT_REQUEST_TYPES = {
    "exam": "Опрос рынка",
    "info": "Просмотр данных",
    "work": "Рабочий запрос",
}

DEFAULT_REQUEST_STATUSES = {
    "new": "Новый запрос",
    "in_progress": "В работе",
    "completed": "Завершен",
    "cancelled": "Отменен",
}

DEFAULT_PRODUCT_CATEGORIES = {
    "wall": "Валл",
    "valve": "Клапан",
    "frame": "Корпус",
}


def seed_reference_data() -> None:
    with current_app.app_context():
        for code, description in DEFAULT_REQUEST_TYPES.items():
            db.session.merge(RequestType(code=code, description=description))

        for code, description in DEFAULT_REQUEST_STATUSES.items():
            db.session.merge(RequestStatus(code=code, description=description))

        for code, description in DEFAULT_PRODUCT_CATEGORIES.items():
            db.session.merge(ProductCategory(code=code, description=description))

        db.session.commit()
