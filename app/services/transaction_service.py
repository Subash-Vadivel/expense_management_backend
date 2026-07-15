from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.common import parse_uuid
from app.models.transaction import CustomFieldValue, Transaction, TransactionType
from app.repositories import transaction_repository
from app.schemas.transaction import (
    CustomFieldValueInput,
    CustomFieldValueResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.category_service import get_category_for_business


def custom_value_to_response(value: dict) -> CustomFieldValueResponse:
    return CustomFieldValueResponse(
        fieldId=value["fieldId"],
        fieldName=value["fieldName"],
        fieldType=value["fieldType"],
        valueNumber=value.get("valueNumber"),
        valueString=value.get("valueString"),
        valueBoolean=value.get("valueBoolean"),
    )


def transaction_to_response(transaction: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=str(transaction.id),
        date=transaction.date,
        categoryId=str(transaction.category_id),
        categoryName=transaction.category_name,
        description=transaction.description,
        amount=float(transaction.amount),
        type=transaction.type,
        customFieldValues=[
            custom_value_to_response(value)
            for value in transaction.custom_field_values
        ],
        createdAt=transaction.created_at,
        updatedAt=transaction.updated_at,
    )


def is_empty_value(value) -> bool:
    return value is None or value == ""


def coerce_custom_field_value(field: dict, raw_value) -> CustomFieldValue | None:
    if is_empty_value(raw_value):
        return None

    field_type = field["type"]
    value_number = None
    value_string = None
    value_boolean = None

    if field_type == "NUMBER":
        if isinstance(raw_value, bool):
            raise ValueError("must be a number")
        try:
            value_number = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("must be a number") from exc
    elif field_type == "STRING":
        if isinstance(raw_value, (dict, list)):
            raise ValueError("must be a string")
        value_string = str(raw_value)
    elif field_type == "BOOLEAN":
        if not isinstance(raw_value, bool):
            raise ValueError("must be true or false")
        value_boolean = raw_value

    return CustomFieldValue(
        field_id=field["id"],
        field_name=field["name"],
        field_type=field_type,
        value_number=value_number,
        value_string=value_string,
        value_boolean=value_boolean,
    )


def validate_custom_field_values(
    category: Category, incoming_values: list[CustomFieldValueInput]
) -> list[dict]:
    definitions = category.custom_fields
    definition_by_id = {field["id"]: field for field in definitions}
    incoming_by_id = {value.fieldId: value.value for value in incoming_values}

    unknown_ids = sorted(set(incoming_by_id) - set(definition_by_id))
    if unknown_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown custom field id: {unknown_ids[0]}",
        )

    values: list[dict] = []
    for field in definitions:
        raw_value = incoming_by_id.get(field["id"])
        if field.get("required", False) and is_empty_value(raw_value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field['name']} is required",
            )
        try:
            custom_value = coerce_custom_field_value(field, raw_value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field['name']} {exc}",
            ) from exc
        if custom_value is not None:
            values.append(custom_value.to_payload())
    return values


async def create_transaction(
    db: AsyncSession,
    payload: TransactionCreate,
    transaction_type: TransactionType,
    business_id: UUID,
    user_id: UUID,
) -> TransactionResponse:
    category = await get_category_for_business(db, payload.categoryId, transaction_type, business_id)
    custom_field_values = validate_custom_field_values(category, payload.customFieldValues)
    transaction = Transaction(
        date=payload.date,
        category_id=category.id,
        category_name=category.name,
        description=payload.description,
        amount=payload.amount,
        type=transaction_type,
        custom_field_values=custom_field_values,
        business_id=business_id,
        created_by=user_id,
    )
    transaction_id = await transaction_repository.create_transaction(db, transaction)
    created = await transaction_repository.find_transaction_by_id(db, transaction_id)
    return transaction_to_response(created)


async def list_transactions(
    db: AsyncSession,
    transaction_type: TransactionType,
    business_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[TransactionResponse]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="startDate cannot be after endDate",
        )

    transactions = await transaction_repository.list_transactions(
        db, transaction_type, business_id, start_date, end_date
    )
    return [transaction_to_response(transaction) for transaction in transactions]


async def update_transaction(
    db: AsyncSession,
    entry_id: str,
    payload: TransactionUpdate,
    transaction_type: TransactionType,
    business_id: UUID,
) -> TransactionResponse:
    existing = await transaction_repository.find_transaction_for_business(
        db, parse_uuid(entry_id, "entry id"), transaction_type, business_id
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    update_data = payload.model_dump(exclude_unset=True, by_alias=True)
    category = None
    if "categoryId" in update_data and update_data["categoryId"]:
        category = await get_category_for_business(db, update_data["categoryId"], transaction_type, business_id)
        existing.category_id = category.id
        existing.category_name = category.name
    elif "customFieldValues" in update_data:
        category = await get_category_for_business(db, str(existing.category_id), transaction_type, business_id)

    if "date" in update_data and update_data["date"] is not None:
        existing.date = update_data["date"]
    if "description" in update_data:
        existing.description = update_data["description"]
    if "amount" in update_data and update_data["amount"] is not None:
        existing.amount = update_data["amount"]
    if category is not None and ("customFieldValues" in update_data or "categoryId" in update_data):
        existing.custom_field_values = validate_custom_field_values(category, payload.customFieldValues or [])
    existing.updated_at = datetime.utcnow()

    await transaction_repository.update_transaction(db, existing)
    updated = await transaction_repository.find_transaction_by_id(db, existing.id)
    return transaction_to_response(updated)


async def delete_transaction(
    db: AsyncSession, entry_id: str, transaction_type: TransactionType, business_id: UUID
) -> None:
    deleted_count = await transaction_repository.delete_transaction(
        db, parse_uuid(entry_id, "entry id"), transaction_type, business_id
    )
    if deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
