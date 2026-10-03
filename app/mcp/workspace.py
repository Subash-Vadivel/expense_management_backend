from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import business_repository
from app.services.business_service import WRITE_FINANCE_ROLES
from app.services.mcp_api_key_service import McpApiKeyAuth


class ToolAccessError(Exception):
    """Raised when the key's user can't use a tool in the requested workspace; reported as a tool error."""


@dataclass(frozen=True)
class WorkspaceContext:
    """What workspace tools act on: the key's user, inside one workspace, with their role there."""

    user_id: UUID
    business_id: UUID
    role: str


async def resolve_workspace(db: AsyncSession, auth: McpApiKeyAuth, workspace_id: object, writes: bool) -> WorkspaceContext:
    if not isinstance(workspace_id, str) or not workspace_id.strip():
        raise ToolAccessError("workspaceId is required. Call list_workspaces to find it.")
    try:
        business_id = UUID(workspace_id.strip())
    except ValueError as exc:
        raise ToolAccessError(f"workspaceId {workspace_id!r} is not a valid id. Call list_workspaces to find it.") from exc
    membership = await business_repository.get_membership(db, business_id, auth.user_id)
    if not membership or membership.status != "active":
        raise ToolAccessError(f"You are not a member of workspace {workspace_id}. Call list_workspaces to see yours.")
    if writes and membership.role not in WRITE_FINANCE_ROLES:
        raise ToolAccessError(
            f"Your role in this workspace ({membership.role}) is read-only, so this tool can't change anything here."
        )
    return WorkspaceContext(user_id=auth.user_id, business_id=business_id, role=membership.role)
