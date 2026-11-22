"""Azure Blob Storage for complaint photos and documents.

  * check_file()        - pure checks (size, real file type from its first bytes). Runs locally, no Azure needed.
  * upload_blob()       - writes the file into the private container.
  * make_read_urls()    - short-lived read-only links (SAS) so the browser can show a private file.

The container stays PRIVATE. Files are never public; a link works for 30 minutes.
We never use the student's file name in the blob name (that could be abused), only a random one.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from core.azure_clients import get_blob_container_client, get_blob_service_client
from core.config import get_blob_settings
from core.constants import MAX_ATTACHMENT_BYTES
from core.errors import PayloadTooLarge, ValidationError

LINK_MINUTES = 30

# (type, extension, how the file must start)
FILE_TYPES = [
    ("image/jpeg", ".jpg", lambda b: b[:3] == b"\xff\xd8\xff"),
    ("image/png", ".png", lambda b: b[:8] == b"\x89PNG\r\n\x1a\n"),
    ("image/webp", ".webp", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
    ("application/pdf", ".pdf", lambda b: b[:5] == b"%PDF-"),
]


def check_file(data: bytes, declared_type: str) -> tuple[str, str]:
    """Returns (content_type, extension) or raises. The real type comes from the bytes, not from the browser."""
    if not data:
        raise ValidationError("The file is empty.")
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise PayloadTooLarge("The file must be under 5 MB.")
    for content_type, extension, looks_right in FILE_TYPES:
        if looks_right(data):
            if declared_type and declared_type.split(";")[0].strip().lower() != content_type:
                raise ValidationError("The file type does not match its content.")
            return content_type, extension
    raise ValidationError("Upload a JPG, PNG, WebP image or a PDF.")


def safe_display_name(name: str) -> str:
    """Only used to show the original name back to people. Never used as a path."""
    name = (name or "file").replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[:150] or "file"


def new_blob_name(complaint_id: int, extension: str) -> str:
    return f"complaints/{complaint_id}/{uuid.uuid4().hex}{extension}"


def upload_blob(blob_name: str, data: bytes, content_type: str) -> None:
    from azure.storage.blob import ContentSettings

    container = get_blob_container_client()
    container.upload_blob(name=blob_name, data=data, overwrite=False,
                          content_settings=ContentSettings(content_type=content_type))


def make_read_urls(blob_names: list[str]) -> dict[str, str]:
    """Maps blob name -> temporary read link. If links cannot be made, returns {} and the page just shows no image."""
    if not blob_names:
        return {}
    try:
        from azure.storage.blob import BlobSasPermissions, generate_blob_sas

        settings = get_blob_settings()
        service = get_blob_service_client()
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=LINK_MINUTES)
        # One Entra-signed "delegation key" is enough for every link in this request.
        key = service.get_user_delegation_key(now - timedelta(minutes=5), expiry)
        urls = {}
        for name in blob_names:
            sas = generate_blob_sas(account_name=service.account_name, container_name=settings.container, blob_name=name,
                                    user_delegation_key=key, permission=BlobSasPermissions(read=True), expiry=expiry)
            urls[name] = f"{settings.account_url}/{settings.container}/{name}?{sas}"
        return urls
    except Exception as err:  # noqa: BLE001 - a storage problem must not break the whole page
        logging.warning("Could not create attachment links: %s", type(err).__name__)
        return {}
