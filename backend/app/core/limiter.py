"""
app/core/limiter.py
-------------------
Shared slowapi Limiter singleton.

Defined here (not in router.py) to avoid circular imports:
  router.py imports ingest.py → ingest.py imports limiter → limiter imports router ✗

Any route module that needs @limiter.limit(...) imports from this module instead.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
