from pydantic import BaseModel, Field


class QueueEntry(BaseModel):
    id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1)
    token: str = Field(..., min_length=1)
    position: int = Field(..., ge=0)
