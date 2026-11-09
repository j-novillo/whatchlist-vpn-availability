"""Google credentials for Docs and, when Workspace allows it, Keep.

Nothing here opens a browser unless the user set GOOGLE_OAUTH_CLIENT_FILE and
there is no saved token yet. Missing files raise ConfigError in Spanish.
"""

import os
from pathlib import Path

from watchlist_enricher.errors import ConfigError

DOCS_SCOPE = "https://www.googleapis.com/auth/documents"
KEEP_SCOPE = "https://www.googleapis.com/auth/keep"


def load_google_credentials(scopes: list[str]):
    """Return google-auth credentials or raise ConfigError."""

    service_account_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    if service_account_file:
        return _service_account(service_account_file, scopes)
    token_file = os.environ.get("GOOGLE_TOKEN_FILE", "").strip()
    client_file = os.environ.get("GOOGLE_OAUTH_CLIENT_FILE", "").strip()
    if token_file and Path(token_file).is_file():
        return _user_token(token_file, scopes)
    if client_file:
        return _installed_app_flow(client_file, token_file, scopes)
    raise ConfigError(
        "Faltan credenciales de Google. Define GOOGLE_SERVICE_ACCOUNT_FILE "
        "o GOOGLE_OAUTH_CLIENT_FILE. Mientras tanto puedes usar --note-file, "
        "--snapshot-file y --dry-run. Ver docs/configuracion.md."
    )


def _service_account(path: str, scopes: list[str]):
    if not Path(path).is_file():
        raise ConfigError(f"No existe GOOGLE_SERVICE_ACCOUNT_FILE: {path}")
    try:
        from google.oauth2 import service_account
    except ImportError as exc:
        raise ConfigError("Falta el paquete google-auth.") from exc
    credentials = service_account.Credentials.from_service_account_file(path, scopes=scopes)
    subject = os.environ.get("GOOGLE_DELEGATED_USER", "").strip()
    if subject:
        credentials = credentials.with_subject(subject)
    return credentials


def _user_token(path: str, scopes: list[str]):
    try:
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise ConfigError("Falta el paquete google-auth.") from exc
    credentials = Credentials.from_authorized_user_file(path, scopes)
    if credentials.expired and credentials.refresh_token:
        from google.auth.transport.requests import Request

        credentials.refresh(Request())
        Path(path).write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def _installed_app_flow(client_file: str, token_file: str, scopes: list[str]):
    if not Path(client_file).is_file():
        raise ConfigError(f"No existe GOOGLE_OAUTH_CLIENT_FILE: {client_file}")
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise ConfigError("Falta el paquete google-auth-oauthlib.") from exc
    flow = InstalledAppFlow.from_client_secrets_file(client_file, scopes)
    credentials = flow.run_local_server(port=0)
    if token_file:
        Path(token_file).write_text(credentials.to_json(), encoding="utf-8")
    return credentials
