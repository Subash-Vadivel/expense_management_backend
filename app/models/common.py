from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status


def parse_uuid(value: str, label: str = "id") -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label}",
        ) from exc
