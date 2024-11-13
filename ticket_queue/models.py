from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field


def _non_empty_string_validator(val: str) -> str:
    if not val:
        raise ValueError("value must not be empty")

    val = val.strip()
    if not val.strip():
        raise ValueError("value cannot contain only whitespace")

    return val


NonEmptyString = Annotated[str, AfterValidator(_non_empty_string_validator)]


class QueueTicket(BaseModel):
    id: int = Field(..., ge=1)
    name: NonEmptyString
    token: str = Field(..., min_length=1)
    position: int = Field(..., ge=0)


class NewTicket(BaseModel):
    name: NonEmptyString
