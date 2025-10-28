from __future__ import annotations

import json
from pathlib import Path

from flask import Response, jsonify

from . import api_bp


def _locate_openapi_file() -> Path | None:
    candidates = [
        Path(__file__).resolve().parents[2] / "openapi" / "openapi.json",
        Path(__file__).resolve().parents[3] / "openapi" / "openapi.json"
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


OPENAPI_PATH = _locate_openapi_file()


def _load_openapi_spec() -> dict | None:
    if not OPENAPI_PATH:
        return None

    try:
        with OPENAPI_PATH.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except (OSError, json.JSONDecodeError):
        return None


SWAGGER_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Handbook API Documentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
    <style>
      body { margin: 0; }
      #swagger-ui { height: 100vh; }
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        window.ui = SwaggerUIBundle({
          url: '/api/openapi.json',
          dom_id: '#swagger-ui'
        });
      };
    </script>
  </body>
</html>
"""


@api_bp.get("/openapi.json")
def openapi_json():
    spec = _load_openapi_spec()
    if spec is None:
        return jsonify({"message": "OpenAPI specification not found"}), 404
    return jsonify(spec)


@api_bp.get("/docs")
def openapi_docs():
    if not OPENAPI_PATH:
        return jsonify({"message": "OpenAPI specification not found"}), 503
    return Response(SWAGGER_HTML, mimetype="text/html")
