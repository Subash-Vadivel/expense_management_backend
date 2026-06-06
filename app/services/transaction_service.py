from __future__ import annotations

from datetime import date, datetime, time, timezone

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.transaction import CustomFieldValue, TransactionModel, TransactionType
from app.repositories import transaction_repository
from app.schemas.transaction import (
    CustomFieldValueInput,
    CustomFieldValueResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.category_service import get_category_for_user


def custom_value_to_response(value: dict) -> CustomFieldValueResponse:
    return CustomFieldValueResponse(
        fieldId=value["fieldId"],
        fieldName=value["fieldName"],
        fieldType=value["fieldType"],
        valueNumber=value.get("valueNumber"),
        valueString=value.get("valueString"),
        valueBoolean=value.get("valueBoolean"),
    )


def transaction_to_response(transaction: dict) -> TransactionResponse:
    stored_date = transaction["date"]
    entry_date = stored_date.date() if isinstance(stored_date, datetime) else stored_date
    return TransactionResponse(
        id=str(transaction["_id"]),
        date=entry_date,
        categoryId=str(transaction["categoryId"]),
        categoryName=transaction["categoryName"],
        description=transaction.get("description"),
        amount=float(transaction["amount"]),
        type=transaction["type"],
        customFieldValues=[
            custom_value_to_response(value)
            for value in transaction.get("customFieldValues", [])
        ],
        createdAt=transaction["createdAt"],
        updatedAt=transaction["updatedAt"],
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
        fieldId=field["id"],
        fieldName=field["name"],
        fieldType=field_type,
        valueNumber=value_number,
        valueString=value_string,
        valueBoolean=value_boolean,
    )


def validate_custom_field_values(
    category: dict, incoming_values: list[CustomFieldValueInput]
) -> list[CustomFieldValue]:
    definitions = category.get("customFields", [])
    definition_by_id = {field["id"]: field for field in definitions}
    incoming_by_id = {value.fieldId: value.value for value in incoming_values}

    unknown_ids = sorted(set(incoming_by_id) - set(definition_by_id))
    if unknown_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown custom field id: {unknown_ids[0]}",
        )

    values: list[CustomFieldValue] = []
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
            values.append(custom_value)
    return values


async def create_transaction(
    db: AsyncIOMotorDatabase,
    payload: TransactionCreate,
    transaction_type: TransactionType,
    user_id: ObjectId,
) -> TransactionResponse:
    category = await get_category_for_user(db, payload.categoryId, transaction_type, user_id)
    custom_field_values = validate_custom_field_values(category, payload.customFieldValues)
    transaction = TransactionModel(
        date=payload.date,
        categoryId=category["_id"],
        categoryName=category["name"],
        description=payload.description,
        amount=payload.amount,
        type=transaction_type,
        customFieldValues=custom_field_values,
        createdBy=user_id,
    )
    transaction_id = await transaction_repository.create_transaction(db, transaction.to_mongo())
    created = await transaction_repository.find_transaction_by_id(db, transaction_id)
    return transaction_to_response(created)


async def list_transactions(
    db: AsyncIOMotorDatabase,
    transaction_type: TransactionType,
    user_id: ObjectId,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[TransactionResponse]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="startDate cannot be after endDate",
        )

    transactions = await transaction_repository.list_transactions(
        db, transaction_type, user_id, start_date, end_date
    )
    return [transaction_to_response(transaction) for transaction in transactions]


async def update_transaction(
    db: AsyncIOMotorDatabase,
    entry_id: str,
    payload: TransactionUpdate,
    transaction_type: TransactionType,
    user_id: ObjectId,
) -> TransactionResponse:
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entry id")

    existing = await transaction_repository.find_transaction_for_user(
        db, ObjectId(entry_id), transaction_type, user_id
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    update_data = payload.model_dump(exclude_unset=True, by_alias=True)
    if "date" in update_data and isinstance(update_data["date"], date):
        update_data["date"] = datetime.combine(update_data["date"], time.min, tzinfo=timezone.utc)

    category = None
    if "categoryId" in update_data and update_data["categoryId"]:
        category = await get_category_for_user(db, update_data["categoryId"], transaction_type, user_id)
        update_data["categoryId"] = category["_id"]
        update_data["categoryName"] = category["name"]
    elif "customFieldValues" in update_data:
        category = await get_category_for_user(db, str(existing["categoryId"]), transaction_type, user_id)

    if category is not None and ("customFieldValues" in update_data or "categoryId" in update_data):
        custom_field_values = validate_custom_field_values(category, payload.customFieldValues or [])
        update_data["customFieldValues"] = [value.to_mongo() for value in custom_field_values]
    update_data["updatedAt"] = datetime.now(timezone.utc)

    await transaction_repository.update_transaction(db, existing["_id"], update_data)
    updated = await transaction_repository.find_transaction_by_id(db, existing["_id"])
    return transaction_to_response(updated)


async def delete_transaction(
    db: AsyncIOMotorDatabase, entry_id: str, transaction_type: TransactionType, user_id: ObjectId
) -> None:
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entry id")
    result = await transaction_repository.delete_transaction(
        db, ObjectId(entry_id), transaction_type, user_id
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
