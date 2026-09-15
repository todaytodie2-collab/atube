# -*- coding: utf-8 -*-
"""
Lightweight Environment Loader for A TuBe
Loads key-value pairs from .env without external dependencies.
"""

import os

def load_env(env_path: str = None) -> dict:
    """Loads variables from .env file into os.environ."""
    if env_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base_dir, ".env")

    env_vars = {}
    if not os.path.exists(env_path):
        return env_vars

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    # Set into os.environ if not already defined
                    if key and key not in os.environ:
                        os.environ[key] = val
                    env_vars[key] = val
    except Exception as e:
        print(f"[EnvLoader] Warning loading .env: {e}")

    return env_vars

# Auto-execute on import
load_env()
