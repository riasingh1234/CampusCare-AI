"""Central configuration for the CampusCare AI backend.

HOW IT WORKS (read this first)
------------------------------
* All settings come from environment variables.
    - Locally, the Azure Functions tools copy the "Values" in local.settings.json
      into environment variables for you.
    - In Azure, you enter the same names under the Function App's application settings.
* Settings are grouped: app, sql, blob, ai, speech. Each group is checked on its own, so a
  problem with AI settings never blocks the SQL code.
* If something is missing or wrong you get a ConfigError that lists the VARIABLE NAMES
  and how to fix them. Values (especially secrets) are never printed.
* There are no passwords for Azure SQL or Blob Storage here. Those use Microsoft Entra
  identities (see azure_clients.py). The only secrets are JWT_SECRET, SPEECH_KEY (only when
  SPEECH_ENABLED=true) and, only if you choose the fallback, AI_FOUNDRY_API_KEY.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

_PLACEHOLDER = re.compile(r"<[^>]*>")
_UUID = re.compile(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
_CONTAINER = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?!-)){1,61}[a-z0-9]$")


class ConfigError(Exception):
    """Raised when settings are missing or invalid. The message never contains values."""

    def __init__(self, group: str, problems: list[str]):
        self.group = group
        self.problems = list(problems)
        lines = "\n".join(f"  - {p}" for p in self.problems)
        super().__init__(f"Problem with the '{group}' settings:\n{lines}")


class Secret:
    """Wraps a secret so it cannot leak through print(), logging or repr()."""

    __slots__ = ("_value",)

    def __init__(self, value: str):
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "Secret(***)"

    __str__ = __repr__


class _Reader:
    """Reads and validates variables for one group, collecting problems as it goes."""

    def __init__(self, group: str):
        self.group = group
        self.problems: list[str] = []

    def text(self, name: str, *, required: bool = True, default: str | None = None) -> str | None:
        raw = os.environ.get(name)
        value = raw.strip() if raw else ""
        if not value:
            if default is not None:
                return default
            if required:
                self.problems.append(
                    f"{name} is missing. Add it to local.settings.json (local) or to the Function App's application settings (Azure)."
                )
            return None
        if _PLACEHOLDER.search(value):
            self.problems.append(f"{name} still contains a placeholder like <...>. Replace it with your real value (where to find each value: docs/azure-setup.md).")
            return None
        return value

    def boolean(self, name: str, default: bool = False) -> bool:
        value = self.text(name, required=False)
        if value is None:
            return default
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        self.problems.append(f"{name} must be true or false.")
        return default

    def integer(self, name: str, default: int, minimum: int, maximum: int) -> int:
        value = self.text(name, required=False)
        if value is None:
            return default
        try:
            number = int(value)
        except ValueError:
            self.problems.append(f"{name} must be a whole number.")
            return default
        if not minimum <= number <= maximum:
            self.problems.append(f"{name} must be between {minimum} and {maximum}.")
            return default
        return number

    def problem(self, message: str) -> None:
        self.problems.append(message)

    def done(self) -> None:
        if self.problems:
            raise ConfigError(self.group, self.problems)


# --------------------------------------------------------------------------- app
@dataclass(frozen=True)
class AppSettings:
    env: str
    allowed_origin: str
    jwt_secret: Secret
    jwt_expiry_minutes: int


def get_app_settings() -> AppSettings:
    r = _Reader("app")
    env = r.text("APP_ENV", required=False, default="local")
    origin = r.text("ALLOWED_ORIGIN")
    if origin and not origin.startswith(("http://", "https://")):
        r.problem("ALLOWED_ORIGIN must start with http:// or https:// (for example http://localhost:5173).")
    secret = r.text("JWT_SECRET")
    if secret and len(secret) < 32:
        r.problem("JWT_SECRET is too short. Use at least 32 random characters (see docs/azure-setup.md for a one-line generator).")
    minutes = r.integer("JWT_EXPIRY_MINUTES", default=60, minimum=5, maximum=1440)
    r.done()
    return AppSettings(env=env, allowed_origin=origin.rstrip("/"), jwt_secret=Secret(secret), jwt_expiry_minutes=minutes)


# ---------------------------------------------------------------------- identity
def get_identity_client_id() -> str | None:
    """Optional. Only needed if the Function App uses a USER-assigned managed identity."""
    r = _Reader("identity")
    value = r.text("AZURE_CLIENT_ID", required=False)
    if value and not _UUID.match(value):
        r.problem("AZURE_CLIENT_ID must be a GUID like 00000000-0000-0000-0000-000000000000, or left empty.")
    r.done()
    return value


# --------------------------------------------------------------------------- sql
@dataclass(frozen=True)
class SqlSettings:
    server: str
    database: str
    driver: str


def get_sql_settings() -> SqlSettings:
    """Azure SQL uses Microsoft Entra authentication only. There is no password setting by design."""
    r = _Reader("sql")
    server = r.text("SQL_SERVER")
    database = r.text("SQL_DATABASE")
    driver = r.text("SQL_ODBC_DRIVER", required=False, default="ODBC Driver 18 for SQL Server")
    if server:
        if "://" in server or ":" in server or "," in server or "/" in server:
            r.problem("SQL_SERVER must be only the server name, like myserver.database.windows.net (no tcp:, https:// or port).")
        elif ".database." not in server:
            r.problem("SQL_SERVER should look like <server-name>.database.windows.net. Copy 'Server name' from the SQL server's Overview page.")
    r.done()
    return SqlSettings(server=server, database=database, driver=driver)


# -------------------------------------------------------------------------- blob
@dataclass(frozen=True)
class BlobSettings:
    account_url: str
    container: str


def get_blob_settings() -> BlobSettings:
    r = _Reader("blob")
    url = r.text("BLOB_ACCOUNT_URL")
    container = r.text("BLOB_CONTAINER_NAME")
    if url and not (url.startswith("https://") and ".blob." in url):
        r.problem("BLOB_ACCOUNT_URL should look like https://<storage-account>.blob.core.windows.net (the account's Blob service endpoint).")
    if container and not _CONTAINER.match(container):
        r.problem("BLOB_CONTAINER_NAME must be 3-63 characters: lowercase letters, numbers and single hyphens, starting and ending with a letter or number.")
    r.done()
    return BlobSettings(account_url=url.rstrip("/"), container=container)


# ---------------------------------------------------------------------------- ai
@dataclass(frozen=True)
class AiSettings:
    enabled: bool
    auth_mode: str                    # "entra" (recommended) or "api_key" (backend-only fallback)
    deployment: str | None            # model deployment name from the Foundry project
    project_endpoint: str | None      # used in entra mode
    resource_endpoint: str | None     # used in api_key mode
    api_key: Secret | None            # used in api_key mode only


def get_ai_settings() -> AiSettings:
    r = _Reader("ai")
    enabled = r.boolean("AI_ENABLED", default=False)
    if not enabled:
        r.done()
        return AiSettings(False, "entra", None, None, None, None)

    mode = (r.text("AI_AUTH_MODE", required=False, default="entra") or "entra").lower()
    if mode not in ("entra", "api_key"):
        r.problem("AI_AUTH_MODE must be 'entra' or 'api_key'.")
    deployment = r.text("AI_FOUNDRY_DEPLOYMENT")
    project_endpoint = resource_endpoint = None
    api_key = None
    if mode == "entra":
        project_endpoint = r.text("AI_FOUNDRY_PROJECT_ENDPOINT")
        if project_endpoint and not (project_endpoint.startswith("https://") and "/api/projects/" in project_endpoint):
            r.problem("AI_FOUNDRY_PROJECT_ENDPOINT should look like https://<resource>.services.ai.azure.com/api/projects/<project>. Copy it from the project's home page in the Foundry portal.")
    elif mode == "api_key":
        resource_endpoint = r.text("AI_FOUNDRY_RESOURCE_ENDPOINT")
        if resource_endpoint and not resource_endpoint.startswith("https://"):
            r.problem("AI_FOUNDRY_RESOURCE_ENDPOINT must start with https://")
        key = r.text("AI_FOUNDRY_API_KEY")
        api_key = Secret(key) if key else None
    r.done()
    return AiSettings(True, mode, deployment, project_endpoint, resource_endpoint, api_key)


# ------------------------------------------------------------------------ speech
@dataclass(frozen=True)
class SpeechSettings:
    enabled: bool
    region: str | None      # for example "centralindia" (the region of your Speech resource)
    key: Secret | None      # stays on the backend. React only ever receives a short-lived token.


def get_speech_settings() -> SpeechSettings:
    """Azure AI Speech. Switched off by default (SPEECH_ENABLED=false) so the rest of the app never depends on it."""
    r = _Reader("speech")
    enabled = r.boolean("SPEECH_ENABLED", default=False)
    if not enabled:
        r.done()
        return SpeechSettings(False, None, None)
    region = r.text("SPEECH_REGION")
    if region and not re.fullmatch(r"[a-z0-9]+", region):
        r.problem("SPEECH_REGION must be a region code like centralindia or eastus (lowercase, no spaces).")
    key = r.text("SPEECH_KEY")
    r.done()
    return SpeechSettings(True, region, Secret(key))


# ----------------------------------------------------------------------- helpers
GROUPS = {
    "app": get_app_settings,
    "identity": get_identity_client_id,
    "sql": get_sql_settings,
    "blob": get_blob_settings,
    "ai": get_ai_settings,
    "speech": get_speech_settings,
}


def validate_all() -> dict[str, list[str]]:
    """Checks every group WITHOUT contacting Azure. Returns {group: [problems]} (empty list = fine)."""
    result: dict[str, list[str]] = {}
    for name, loader in GROUPS.items():
        try:
            loader()
            result[name] = []
        except ConfigError as err:
            result[name] = err.problems
    return result


def load_local_settings_file(path: str | Path | None = None) -> bool:
    """Copies "Values" from local.settings.json into the environment (real env vars win).

    Only the check_config.py script needs this: the Functions host already does it when you run `func start`.
    Returns False if the file does not exist.
    """
    file = Path(path) if path else Path(__file__).resolve().parents[1] / "local.settings.json"
    if not file.exists():
        return False
    values = json.loads(file.read_text(encoding="utf-8")).get("Values", {})
    for key, value in values.items():
        if isinstance(value, str):
            os.environ.setdefault(key, value)
    return True
