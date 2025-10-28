from __future__ import annotations

from flask import Flask, jsonify
from sqlalchemy import text

from .config import load_settings
from .database import init_database, db
from .routes import api_bp
from .seed import seed_reference_data


def _apply_schema_migrations() -> None:
    statements = [
        """
        alter table if exists products
        alter column part_number type varchar(100) using part_number::text,
        alter column pos_scheme type varchar(100) using pos_scheme::text
        """,
        """
        alter table if exists request_items
        alter column part_number type varchar(100) using part_number::text,
        alter column pos_scheme type varchar(100) using pos_scheme::text
        """
    ]

    for statement in statements:
        try:
            db.session.execute(text(statement))
            db.session.commit()
        except Exception:
            db.session.rollback()


def create_app() -> Flask:
    settings = load_settings()
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=settings.db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=settings.secret_key,
        JSON_SORT_KEYS=False,
    )

    init_database(app)

    app.register_blueprint(api_bp)

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"message": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):  # pragma: no cover - generic guard
        app.logger.exception("Unhandled server error: %s", error)
        return jsonify({"message": "Internal server error"}), 500

    with app.app_context():
        db.create_all()
        _apply_schema_migrations()
        seed_reference_data()

    return app
