from flask import jsonify

from ..database import db
from . import api_bp


@api_bp.get("/health")
def healthcheck():
    db.session.execute(db.text("select 1"))
    return jsonify({"status": "ok"})
