"""Shared slowapi rate-limiter instance.

Imported by main.py (middleware setup) and any router that decorates endpoints.
Keeping it in a separate module avoids circular imports.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
