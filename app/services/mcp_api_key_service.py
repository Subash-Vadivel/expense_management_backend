from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_secret, encrypt_secret
from app.models.common import parse_uuid
from app.models.mcp_api_key import McpApiKey
from app.repositories import mcp_api_key_repository
from app.schemas.mcp_api_key import McpApiKeyCreate, McpApiKeyCreateResponse, McpApiKeyResponse, McpApiKeyRevealResponse

KEY_PREFIX = "lgl_mcp_"
# Keys issued before the rename still authenticate.
LEGACY_KEY_PREFIXES = ("farm_mcp_",)


@dataclass(frozen=True)
class McpApiKeyAuth:
    user_id: UUID
    business_id: UUID
    # The key creator's current role in the business; tools are limited by it.
    role: str


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"


def api_key_to_response(api_key: McpApiKey) -> McpApiKeyResponse:
    return McpApiKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        keyPrefix=api_key.key_prefix,
        enabled=api_key.enabled,
        createdAt=api_key.created_at,
        lastUsedAt=api_key.last_used_at,
        disabledAt=api_key.disabled_at,
        canReveal=api_key.encrypted_key is not None,
    )


async def create_api_key(
    db: AsyncSession,
    payload: McpApiKeyCreate,
    business_id: UUID,
    user_id: UUID,
) -> McpApiKeyCreateResponse:
    raw_key = generate_api_key()
    key_prefix = raw_key[:18]
    api_key = McpApiKey(
        name=" ".join(payload.name.strip().split()),
        key_hash=hash_api_key(raw_key),
        key_prefix=key_prefix,
        encrypted_key=encrypt_secret(raw_key),
        business_id=business_id,
        created_by=user_id,
    )
    api_key_id = await mcp_api_key_repository.create_api_key(db, api_key)
    created = await mcp_api_key_repository.find_api_key_by_id(db, api_key_id)
    return McpApiKeyCreateResponse(**api_key_to_response(created).model_dump(), apiKey=raw_key)


async def list_api_keys(db: AsyncSession, business_id: UUID) -> list[McpApiKeyResponse]:
    api_keys = await mcp_api_key_repository.list_api_keys_for_business(db, business_id)
    return [api_key_to_response(api_key) for api_key in api_keys]


async def set_api_key_enabled(
    db: AsyncSession,
    api_key_id: str,
    business_id: UUID,
    enabled: bool,
) -> McpApiKeyResponse:
    existing = await mcp_api_key_repository.find_api_key_for_business(
        db, parse_uuid(api_key_id, "API key id"), business_id
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    existing.enabled = enabled
    existing.disabled_at = None if enabled else datetime.utcnow()
    await mcp_api_key_repository.update_api_key(db, existing)
    updated = await mcp_api_key_repository.find_api_key_by_id(db, existing.id)
    return api_key_to_response(updated)


async def reveal_api_key(db: AsyncSession, api_key_id: str, business_id: UUID) -> McpApiKeyRevealResponse:
    api_key = await mcp_api_key_repository.find_api_key_for_business(
        db, parse_uuid(api_key_id, "API key id"), business_id
    )
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    raw_key = decrypt_secret(api_key.encrypted_key) if api_key.encrypted_key else None
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This key can't be copied because it was created before keys were stored. Create a new key instead.",
        )
    return McpApiKeyRevealResponse(apiKey=raw_key)


async def delete_api_key(db: AsyncSession, api_key_id: str, business_id: UUID) -> None:
    deleted_count = await mcp_api_key_repository.delete_api_key(
        db, parse_uuid(api_key_id, "API key id"), business_id
    )
    if deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")


async def authenticate_api_key(db: AsyncSession, raw_key: str) -> McpApiKeyAuth | None:
    if not raw_key.startswith((KEY_PREFIX, *LEGACY_KEY_PREFIXES)):
        return None
    row = await mcp_api_key_repository.find_api_key_with_creator_membership(db, hash_api_key(raw_key))
    if not row:
        return None
    api_key, membership = row
    if not api_key.enabled:
        return None
    # A key never has more access than the person who created it has right now.
    if not membership or membership.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user who created this API key no longer has access to this business",
        )
    api_key.last_used_at = datetime.utcnow()
    await mcp_api_key_repository.update_api_key(db, api_key)
    return McpApiKeyAuth(user_id=api_key.created_by, business_id=api_key.business_id, role=membership.role)
