"""
Shared Pydantic helpers used across every model.

PyObjectId  – converts bson.ObjectId ↔ str transparently so FastAPI can
              serialise ObjectIds in JSON responses without custom encoders.
"""

from __future__ import annotations

from bson import ObjectId
from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import BeforeValidator
from typing import Annotated


def _coerce_object_id(v: object) -> str:
    """Accept ObjectId, any valid 24-hex string, or an existing str."""
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    if v is None:
        return v  # type: ignore[return-value]
    raise ValueError(f"Invalid ObjectId value: {v!r}")


# Annotated type alias – use this for every _id / *_id field
PyObjectId = Annotated[str, BeforeValidator(_coerce_object_id)]


class MongoBaseModel(BaseModel):
    """
    Base for all MongoDB document models.

    * populate_by_name=True  → allows both `id` and `_id` aliases
    * arbitrary_types_allowed → accepts ObjectId from PyMongo/Motor cursors
    * json_encoders          → serialise datetime to ISO-8601 strings
    """
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
