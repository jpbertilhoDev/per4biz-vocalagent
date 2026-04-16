"""Google People v1 API wrapper for Vox agent — contacts search.

Exposes:
    - search_contacts(user_id, query, max_results) — search contacts by name/email
    - list_contacts(user_id, max_results) — list recent contacts
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient import discovery

from app.config import get_settings
from app.logging import get_logger
from app.services.gmail import _decode_bytea, _encode_bytea, _select_primary_account
from app.services import crypto, supabase_client

logger = get_logger(__name__)

_TOKEN_URI = "https://oauth2.googleapis.com/token"
_DEFAULT_MAX_RESULTS = 20


def _get_valid_credentials(user_id: str) -> Credentials:
    """Build valid Google credentials with refresh — mirrors gmail pattern."""
    settings = get_settings()
    sb = supabase_client.get_supabase_admin()

    rows: list[dict[str, Any]] = (
        sb.table("google_accounts").select("*").eq("user_id", user_id).execute().data
    )
    row = _select_primary_account(rows)

    refresh_token = _decode_bytea(row["refresh_token_encrypted"])
    refresh_plaintext = crypto.decrypt(refresh_token).decode("utf-8")

    access_plaintext: str | None = None
    access_cipher = row.get("access_token_encrypted")
    if access_cipher:
        access_bytes = _decode_bytea(access_cipher)
        access_plaintext = crypto.decrypt(access_bytes).decode("utf-8")

    credentials = Credentials(
        token=access_plaintext,
        refresh_token=refresh_plaintext,
        token_uri=_TOKEN_URI,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=row.get("scopes") or [],
    )

    if credentials.expired:
        credentials.refresh(Request())
        logger.info("contacts.credentials.refreshed", account_id=row.get("id"))
        new_token = credentials.token
        if new_token:
            new_expiry = getattr(credentials, "expiry", None)
            if new_expiry is None:
                new_expiry_iso = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
            else:
                if new_expiry.tzinfo is None:
                    new_expiry_iso = new_expiry.replace(tzinfo=UTC).isoformat()
                else:
                    new_expiry_iso = new_expiry.isoformat()
            new_cipher = crypto.encrypt(new_token.encode("utf-8"))
            sb.table("google_accounts").update(
                {
                    "access_token_encrypted": _encode_bytea(new_cipher),
                    "access_token_expires_at": new_expiry_iso,
                }
            ).eq("id", row["id"]).execute()

    return credentials


def _parse_contact(person: dict[str, Any]) -> dict[str, Any]:
    """Extract relevant fields from a People API person resource."""
    names = person.get("names", []) or []
    emails = person.get("emailAddresses", []) or []
    phones = person.get("phoneNumbers", []) or []
    organizations = person.get("organizations", []) or []

    display_name = names[0].get("displayName", "") if names else ""
    given_name = names[0].get("givenName", "") if names else ""
    family_name = names[0].get("familyName", "") if names else ""

    email_list = [e.get("value", "") for e in emails if e.get("value")]
    phone_list = [p.get("value", "") for p in phones if p.get("value")]

    organization = ""
    title = ""
    if organizations:
        org = organizations[0]
        organization = org.get("name", "")
        title = org.get("title", "")

    return {
        "resource_name": person.get("resourceName", ""),
        "display_name": display_name,
        "given_name": given_name,
        "family_name": family_name,
        "emails": email_list,
        "phones": phone_list,
        "organization": organization,
        "title": title,
    }


def search_contacts(
    user_id: str,
    query: str,
    max_results: int = _DEFAULT_MAX_RESULTS,
) -> dict[str, Any]:
    """Search contacts by name or email.

    Args:
        user_id: UUID of the user.
        query: Search string (name or email fragment).
        max_results: Maximum contacts to return.

    Returns:
        {"contacts": [...], "count": int}
    """
    creds = _get_valid_credentials(user_id)
    service = discovery.build("people", "v1", credentials=creds, cache_discovery=False)

    result: dict[str, Any] = (
        service.people()
        .searchContacts(
            query=query,
            pageSize=max_results,
            readMask="names,emailAddresses,phoneNumbers,organizations",
        )
        .execute()
    )

    people = result.get("results", []) or []
    contacts = [_parse_contact(p.get("person", {})) for p in people if p.get("person")]

    logger.info("contacts.search", query_len=len(query), contact_count=len(contacts))
    return {"contacts": contacts, "count": len(contacts)}


def list_contacts(
    user_id: str,
    max_results: int = _DEFAULT_MAX_RESULTS,
) -> dict[str, Any]:
    """List recent contacts ordered by last interaction.

    Args:
        user_id: UUID of the user.
        max_results: Maximum contacts to return.

    Returns:
        {"contacts": [...], "count": int}
    """
    creds = _get_valid_credentials(user_id)
    service = discovery.build("people", "v1", credentials=creds, cache_discovery=False)

    result: dict[str, Any] = (
        service.people()
        .connections()
        .list(
            resourceName="people/me",
            pageSize=max_results,
            personFields="names,emailAddresses,phoneNumbers,organizations",
            sortOrder="LAST_MODIFIED_ASCENDING",
        )
        .execute()
    )

    people = result.get("connections", []) or []
    contacts = [_parse_contact(p) for p in people]

    logger.info("contacts.list", contact_count=len(contacts))
    return {"contacts": contacts, "count": len(contacts)}
