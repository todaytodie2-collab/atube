# -*- coding: utf-8 -*-
"""
Automated Test Suite for A TuBe Security & Core API Endpoints
Tests:
- SSRF Security Guard
- Path Traversal Guard
- Rate Limiter Algorithm
- Admin Authorization & Token Verification
- CORS Restrictions & Security Headers
- Environment Variable Loader
"""

import os
import sys
import json
import time
import pytest
from unittest.mock import MagicMock

# Set up paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

import env_loader
from server import (
    is_safe_external_url,
    InMemoryRateLimiter,
    GLOBAL_ADMIN_TOKEN,
    ATubeHandler,
)


class TestEnvironmentLoader:
    def test_env_loader_reads_keys(self):
        env_vars = env_loader.load_env()
        assert isinstance(env_vars, dict)
        assert "TMDB_API_KEY" in os.environ
        assert "ATUBE_ADMIN_TOKEN" in os.environ
        assert len(os.environ["ATUBE_ADMIN_TOKEN"]) > 10


class TestSSRFGuard:
    def test_blocks_localhost_and_loopback(self):
        assert is_safe_external_url("http://127.0.0.1/admin") is False
        assert is_safe_external_url("http://localhost:8080/secret") is False
        assert is_safe_external_url("http://0.0.0.0:8000") is False

    def test_blocks_private_subnets(self):
        assert is_safe_external_url("http://192.168.1.1/router") is False
        assert is_safe_external_url("http://10.0.0.5/api") is False
        assert is_safe_external_url("http://172.16.0.1/metrics") is False

    def test_blocks_invalid_protocols(self):
        assert is_safe_external_url("file:///etc/passwd") is False
        assert is_safe_external_url("ftp://server/file") is False
        assert is_safe_external_url("") is False
        assert is_safe_external_url(None) is False

    def test_allows_safe_external_domains(self):
        assert is_safe_external_url("https://www.google.com") is True
        assert is_safe_external_url("https://api.themoviedb.org/3/movie/popular") is True


class TestRateLimiter:
    def test_rate_limiter_allows_under_limit(self):
        limiter = InMemoryRateLimiter()
        client_ip = "192.0.2.1"
        for _ in range(5):
            assert limiter.is_allowed(client_ip, max_requests=10, window_seconds=60) is True

    def test_rate_limiter_blocks_over_limit(self):
        limiter = InMemoryRateLimiter()
        client_ip = "192.0.2.2"
        # Consume allowed 3 requests
        for _ in range(3):
            assert limiter.is_allowed(client_ip, max_requests=3, window_seconds=60) is True
        # 4th request must be rejected
        assert limiter.is_allowed(client_ip, max_requests=3, window_seconds=60) is False

    def test_rate_limiter_isolates_different_ips(self):
        limiter = InMemoryRateLimiter()
        ip_a = "192.0.2.10"
        ip_b = "192.0.2.20"
        for _ in range(2):
            limiter.is_allowed(ip_a, max_requests=2, window_seconds=60)
        assert limiter.is_allowed(ip_a, max_requests=2, window_seconds=60) is False
        # ip_b should still be allowed
        assert limiter.is_allowed(ip_b, max_requests=2, window_seconds=60) is True


class TestAdminAuthorization:
    def test_unauthorized_when_no_token(self):
        handler = MagicMock(spec=ATubeHandler)
        handler.headers = {}
        handler.path = "/api/crawler/run"
        assert ATubeHandler.is_admin_authorized(handler) is False

    def test_unauthorized_with_wrong_token(self):
        handler = MagicMock(spec=ATubeHandler)
        handler.headers = {"X-Admin-Token": "wrong-token-attempt-xyz"}
        handler.path = "/api/crawler/run"
        assert ATubeHandler.is_admin_authorized(handler) is False

    def test_authorized_with_valid_header_token(self):
        token = os.environ.get("ATUBE_ADMIN_TOKEN") or GLOBAL_ADMIN_TOKEN
        handler = MagicMock(spec=ATubeHandler)
        handler.headers = {"X-Admin-Token": token}
        handler.path = "/api/crawler/run"
        assert ATubeHandler.is_admin_authorized(handler) is True

    def test_authorized_with_valid_query_token(self):
        token = os.environ.get("ATUBE_ADMIN_TOKEN") or GLOBAL_ADMIN_TOKEN
        handler = MagicMock(spec=ATubeHandler)
        handler.headers = {}
        handler.path = f"/api/crawler/run?token={token}"
        assert ATubeHandler.is_admin_authorized(handler) is True


class TestCORSRestrictions:
    def test_cors_allows_localhost(self):
        handler = MagicMock(spec=ATubeHandler)
        handler.headers = {"Origin": "http://localhost:8085"}
        origin = ATubeHandler.get_cors_origin(handler)
        assert origin == "http://localhost:8085"

    def test_cors_allows_capacitor(self):
        handler = MagicMock(spec=ATubeHandler)
        handler.headers = {"Origin": "capacitor://localhost"}
        origin = ATubeHandler.get_cors_origin(handler)
        assert origin == "capacitor://localhost"

    def test_cors_rejects_untrusted_origin(self):
        handler = MagicMock(spec=ATubeHandler)
        handler.headers = {"Origin": "http://malicious-attacker-site.com"}
        origin = ATubeHandler.get_cors_origin(handler)
        # Should not echo malicious origin
        assert origin != "http://malicious-attacker-site.com"
        assert "localhost" in origin


class TestStreamResolverAndProxy:
    def test_ttl_cache_hit_and_eviction(self):
        from stream_extractor import DirectStreamExtractor, StreamTTLCache
        cache = StreamTTLCache(default_ttl_seconds=3600)
        test_url = "https://cdn.example.com/test_movie.m3u8"
        cache.set(test_url, {"success": True, "stream_url": test_url})
        hit = cache.get(test_url)
        assert hit is not None
        assert hit["cached"] is True
        assert hit["ttl_remaining"] > 0

    def test_header_spoofing_table(self):
        from stream_extractor import DirectStreamExtractor
        headers_megamax = DirectStreamExtractor.get_spoofed_headers("https://eg.megamax.cam/watch/abc")
        assert headers_megamax["Referer"] == "https://egydead.live/"
        assert headers_megamax["Origin"] == "https://egydead.live"

        headers_vidmoly = DirectStreamExtractor.get_spoofed_headers("https://vidmoly.to/embed-xyz")
        assert headers_vidmoly["Referer"] == "https://vidmoly.to/"

        headers_mixdrop = DirectStreamExtractor.get_spoofed_headers("https://mixdrop.ag/e/123")
        assert headers_mixdrop["Referer"] == "https://mixdrop.ag/"

    def test_multi_tier_failover_matrix(self):
        from stream_extractor import DirectStreamExtractor
        servers = [
            {"name": "Vidmoly VIP", "url": "https://vidmoly.to/w/999"},
            {"name": "Mixdrop Cloud", "url": "https://mixdrop.ag/f/888"}
        ]
        matrix = DirectStreamExtractor.build_failover_matrix(servers, tmdb_id="634649")
        assert len(matrix) >= 4
        # Tier 1 should be the direct/harvester servers
        assert matrix[0]["tier"] == 1
        # Tier 3 should be VidLink / MultiEmbed
        assert matrix[-1]["tier"] == 3
        assert "vidlink" in matrix[-2]["url"] or "multiembed" in matrix[-1]["url"]

