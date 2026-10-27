from slowapi import Limiter
from slowapi.util import get_remote_address

# Limit traffic keyed by client remote IP address
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
