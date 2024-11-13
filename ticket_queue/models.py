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
    id: int = Field(..., ge=1, description="Unique ID of the ticket.")
    name: NonEmptyString = Field(..., description="Display name for ticket.")
    token: str = Field(
        ...,
        min_length=1,
        description=(
            "Ticket token, non-admin clients must provide this to retrieve or"
            "modify the ticket associated with the token."
        ),
    )
    position: int = Field(
        ..., ge=0, description="Position in queue; 0 means front of queue"
    )
    timestamp: int = Field(
        ...,
        gt=0,
        description=(
            "Approximate of ticket creation in seconds since Unix epoch "
            "(1970-01-01 00:00:00 UTC)"
        ),
    )


class NewTicket(BaseModel):
    name: NonEmptyString
