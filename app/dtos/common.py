"""Shared DTO primitives."""

from pydantic import BaseModel, ConfigDict


class BaseDTO(BaseModel):
    """Base DTO with shared Pydantic configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
    )
