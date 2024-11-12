from typing import Annotated

import fastapi

from models import NewQueueEntry, QueueEntry
from queuedb import QueueConnection

app = fastapi.FastAPI()
api = fastapi.APIRouter(prefix="/api")


def get_queue_connection():
    with QueueConnection("queue.sqlite") as con:
        con.create()
        yield con


Connection = Annotated[
    QueueConnection,
    fastapi.Depends(get_queue_connection)
]


class EntryNotFound(fastapi.HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="Entry not found")


class Unauthorized(fastapi.HTTPException):
    def __init__(self):
        super().__init__(status_code=401, detail="Unauthorized")


@api.get("/entry/{id}")
def get_entry(
    id: int,
    connection: Connection,
    token: str | None = None,
) -> QueueEntry:
    if not token:
        raise EntryNotFound()

    entry = connection.get(id)
    if entry and entry.token == token:
        return entry

    raise EntryNotFound()


@api.get("/entries")
def get_all_entries(
    connection: Connection,
    limit: Annotated[int | None, fastapi.Query(min=1)] = None,
) -> list[QueueEntry]:
    # TODO: needs admin auth
    return connection.get_all(limit=limit)


@api.post("/entries", status_code=201)
def new_entry(new_entry: NewQueueEntry, connection: Connection) -> QueueEntry:
    return connection.enqueue(new_entry.name)


AuthHeaderParam = Annotated[str | None, fastapi.Header()]


def get_token_from_header(val: str) -> str | None:
    split_val = val.split(maxsplit=1)
    if len(split_val) < 2 or split_val[0] != 'Token':
        return None

    return split_val[1] or None


@api.delete("/entry/{id}", status_code=204)
def delete_entry(
    id: int,
    connection: Connection,
    authorization: AuthHeaderParam = None,
) -> None:
    token = get_token_from_header(authorization) if authorization else None
    if not token:
        raise fastapi.HTTPException(status_code=401, detail="Unauthorized")

    entry = connection.get(id)
    if not entry:
        raise EntryNotFound()

    if entry.token != token:
        raise Unauthorized()

    connection.remove(id)


app.include_router(api)
