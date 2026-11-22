"""Connection helpers for Azure SQL, Blob Storage and Microsoft Foundry.

*** STATUS: UNTESTED ***
These helpers are written from Microsoft's documentation but have NOT been run against real
Azure resources. Nothing in the app calls them yet. Mark each one "verified" in
docs/azure-setup.md only after you have run it successfully.

One identity, two places
------------------------
All helpers share a single DefaultAzureCredential:
  * On your computer it uses the account you signed in with:  az login
  * In Azure it uses the Function App's managed identity (no secret anywhere).
If the Function App uses a USER-assigned managed identity, set AZURE_CLIENT_ID to its client ID.

Packages are imported inside the functions so that config checks work even before every
package is installed.
"""
from __future__ import annotations

import struct
from contextlib import contextmanager
from functools import lru_cache

from .config import (
    ConfigError,
    get_ai_settings,
    get_blob_settings,
    get_identity_client_id,
    get_sql_settings,
)

SQL_SCOPE = "https://database.windows.net/.default"
SQL_COPT_SS_ACCESS_TOKEN = 1256  # ODBC attribute that lets us pass an Entra access token


@lru_cache(maxsize=1)
def get_credential():
    """UNTESTED. Returns the shared Entra credential (CLI login locally, managed identity in Azure)."""
    from azure.identity import DefaultAzureCredential

    client_id = get_identity_client_id()
    if client_id:
        return DefaultAzureCredential(managed_identity_client_id=client_id)
    return DefaultAzureCredential()


# --------------------------------------------------------------------- Azure SQL
def _open_sql_connection(autocommit: bool = False):
    import pyodbc  # needs Microsoft ODBC Driver 18 installed on the machine

    s = get_sql_settings()
    token = get_credential().get_token(SQL_SCOPE).token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token)}s", len(token), token)
    # No user name, password or Authentication= keyword: the access token IS the login.
    conn_str = (
        f"Driver={{{s.driver}}};Server=tcp:{s.server},1433;Database={s.database};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}, autocommit=autocommit)


@contextmanager
def sql_connection(autocommit: bool = False):
    """UNTESTED. Use as:  with sql_connection() as conn: ...   (commits on success, rolls back on error).

    Always pass values to cursor.execute() as parameters, never by building SQL text:
        cursor.execute("SELECT * FROM Users WHERE Email = ?", email)
    """
    conn = _open_sql_connection(autocommit)
    try:
        yield conn
        if not autocommit:
            conn.commit()
    except Exception:
        if not autocommit:
            conn.rollback()
        raise
    finally:
        conn.close()


# ----------------------------------------------------------------- Blob Storage
def get_blob_service_client():
    """UNTESTED. Blob client authenticated with Entra (needs 'Storage Blob Data Contributor')."""
    from azure.storage.blob import BlobServiceClient

    return BlobServiceClient(account_url=get_blob_settings().account_url, credential=get_credential())


def get_blob_container_client():
    """UNTESTED. Client for the complaint-images container named in BLOB_CONTAINER_NAME."""
    return get_blob_service_client().get_container_client(get_blob_settings().container)


# ---------------------------------------------------------------------- Foundry
@lru_cache(maxsize=1)
def _foundry_project_client():
    from azure.ai.projects import AIProjectClient

    return AIProjectClient(endpoint=get_ai_settings().project_endpoint, credential=get_credential())


@lru_cache(maxsize=1)
def get_foundry_client():
    """UNTESTED. Returns an OpenAI-compatible client for the model deployment in your Foundry project.

    entra mode (recommended): Microsoft's azure-ai-projects SDK. Entra ID is the ONLY sign-in
        method that SDK supports. Needs the 'Foundry User' role.
    api_key mode (fallback): the standard `openai` package pointed at the resource's /openai/v1/
        endpoint. The key stays on the backend and is never sent to React.

    Call it like:  client.responses.create(model=get_ai_settings().deployment, input="...")
    """
    s = get_ai_settings()
    if not s.enabled:
        raise ConfigError("ai", ["AI_ENABLED is false, so the Azure AI client is switched off. Use the rule-based classifier instead."])
    if s.auth_mode == "entra":
        return _foundry_project_client().get_openai_client()

    from openai import OpenAI

    return OpenAI(base_url=s.resource_endpoint.rstrip("/") + "/openai/v1/", api_key=s.api_key.reveal())
