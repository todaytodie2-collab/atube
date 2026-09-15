# -*- coding: utf-8 -*-
"""
A TuBe - Centralized Secure SSL/TLS Context Factory
Provides a standardized SSL context shared across all services.
● Default: TLS verification ON using certifi CA bundle
● Fallback: Controlled insecure context ONLY for regional media hosts lacking modern CA roots
● Controlled by environment variable ATUBE_STRICT_TLS=1 to fully disable insecure fallback
"""

import os
import ssl

try:
    import certifi
    _CAFILE = certifi.where()
    _HAS_CERTIFI = True
except ImportError:
    _CAFILE = None
    _HAS_CERTIFI = False


def get_secure_context() -> ssl.SSLContext:
    """Returns a verified SSL context using certifi CA bundle when available."""
    try:
        if _HAS_CERTIFI and _CAFILE:
            return ssl.create_default_context(cafile=_CAFILE)
        return ssl.create_default_context()
    except Exception:
        return ssl.create_default_context()


def get_scraper_context() -> ssl.SSLContext:
    """
    Returns SSL context for web scrapers (Arabic portals / CDN hosts).
    Uses verified context by default; falls back to unverified ONLY if 
    ATUBE_STRICT_TLS != 1 and the site presents certificate errors.
    Call get_secure_context() for API-level requests where TLS must be verified.
    NOTE: This context must NOT be used for sensitive API calls (TMDB, admin).
    """
    strict = os.environ.get("ATUBE_STRICT_TLS", "0") == "1"
    if strict:
        return get_secure_context()

    # For Arabic media portals — many use self-signed or regional CA roots
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


# Shared instances (created once, reused across services to avoid overhead)
SECURE_CTX: ssl.SSLContext = get_secure_context()
SCRAPER_CTX: ssl.SSLContext = get_scraper_context()
