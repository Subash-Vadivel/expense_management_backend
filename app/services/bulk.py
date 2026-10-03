from __future__ import annotations

from fastapi import HTTPException, status

MAX_BULK_ITEMS = 20


def item_error_message(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        return str(detail.get("message") or detail)
    return str(detail)


def bulk_rejected(errors: list[dict]) -> HTTPException:
    """All-or-nothing bulk create: report every invalid item; nothing was saved."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "bulk_rejected",
            "message": f"{len(errors)} item(s) are invalid, so nothing was saved. Fix them and send the batch again.",
            "errors": errors,
        },
    )
