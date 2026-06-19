"""OAuth provider configuration."""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth

from web.config import get_settings

oauth = OAuth()

settings = get_settings()

if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
