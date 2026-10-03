from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.mcp_api_key_service import McpApiKeyAuth
from app.mcp.tools.list_arguments import TransactionListArguments
from app.services.transaction_service import create_transaction, delete_transaction, list_transactions, update_transaction


async def handle_list_transactions(
    db: AsyncSession,
    auth: McpApiKeyAuth,
    transaction_type: str,
    arguments: dict,
) -> object:
    args = TransactionListArguments(**arguments)
    page = await list_transactions(
        db,
        transaction_type,
        auth.business_id,
        args.startDate,
        args.endDate,
        args.limit,
        args.offset,
        args.search,
        args.sort,
        args.order,
    )
    return jsonable_encoder(page)


async def handle_create_transaction(
    db: AsyncSession,
    auth: McpApiKeyAuth,
    transaction_type: str,
    arguments: dict,
) -> object:
    payload = TransactionCreate(**arguments)
    return jsonable_encoder(await create_transaction(db, payload, transaction_type, auth.business_id, auth.user_id))


async def handle_update_transaction(
    db: AsyncSession,
    auth: McpApiKeyAuth,
    transaction_type: str,
    arguments: dict,
) -> object:
    entry_id = arguments["id"]
    payload = TransactionUpdate(**{key: value for key, value in arguments.items() if key != "id"})
    return jsonable_encoder(await update_transaction(db, entry_id, payload, transaction_type, auth.business_id))


async def handle_delete_transaction(
    db: AsyncSession,
    auth: McpApiKeyAuth,
    transaction_type: str,
    arguments: dict,
) -> object:
    await delete_transaction(db, arguments["id"], transaction_type, auth.business_id)
    return {"deleted": True, "id": arguments["id"], "type": transaction_type}
