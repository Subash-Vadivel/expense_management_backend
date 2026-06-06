from __future__ import annotations

from datetime import date, datetime, time, timezone

from bson import ObjectId


def user_ownership_filter(user_id: ObjectId) -> dict:
    return {"$in": [user_id, str(user_id)]}


def date_range_filter(start_date: date | None = None, end_date: date | None = None) -> dict:
    date_filter = {}
    if start_date:
        date_filter["$gte"] = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    if end_date:
        date_filter["$lte"] = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
    return date_filter
