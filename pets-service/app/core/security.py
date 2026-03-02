import os

import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Request

from app.exceptions.pet_exceptions import InvalidTokenError


FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")

if not FIREBASE_CREDENTIALS:
    raise ValueError("FIREBASE_CREDENTIALS not set")

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CREDENTIALS)
    firebase_admin.initialize_app(cred)


def verify_token(request: Request) -> dict:
    """Extracts and verifies the Firebase ID token from the Authorization header.

    Raises:
        InvalidTokenError: If token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise InvalidTokenError("Missing token")

    try:
        token = auth_header.split(" ")[1]
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        raise InvalidTokenError("Invalid token")
