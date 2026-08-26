from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def load_service_account(service_account_file: str) -> dict[str, Any]:
    path = Path(service_account_file).expanduser()
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError("Firebase service account file must contain a JSON object")
    return payload


def create_firestore_client(service_account_file: str) -> Any:
    try:
        app = firebase_admin.get_app()
    except ValueError:
        payload = load_service_account(service_account_file)
        app = firebase_admin.initialize_app(credentials.Certificate(payload))
    return firestore.client(app=app)
