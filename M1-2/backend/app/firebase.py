from __future__ import annotations

import json
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore


def create_firestore_client(service_account_json: str) -> Any:
    try:
        app = firebase_admin.get_app()
    except ValueError:
        payload = json.loads(service_account_json)
        app = firebase_admin.initialize_app(credentials.Certificate(payload))
    return firestore.client(app=app)
