"""
Shared Flask extension instances for WikiEval.

Extensions that need to be accessed from blueprints or other modules
are instantiated here to avoid circular import issues.
"""

import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

_storage_uri = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=['60/minute'],
    storage_uri=_storage_uri,
)
