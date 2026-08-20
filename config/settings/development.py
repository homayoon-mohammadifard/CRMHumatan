"""Development settings — safe defaults for local work, not for production."""

from .base import *  # noqa: F403
from .base import env

DEBUG = True

# In development we also allow the DRF browsable API renderer for convenience.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

INSTALLED_APPS += []  # noqa: F405 — placeholder for dev-only apps (e.g. debug toolbar) later

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])
