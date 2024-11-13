from typing import Annotated

import fastapi

from ticket_queue.models import NewTicket, QueueTicket
from ticket_queue.ticket_queue import QueueConnection


class TicketNotFound(fastapi.HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="Ticket not found")


class Unauthorized(fastapi.HTTPException):
    def __init__(self):
        super().__init__(status_code=401, detail="Unauthorized")


OptionalHeader = Annotated[str | None, fastapi.Header()]


def _is_admin(authorization: OptionalHeader = None):
    if not authorization:
        raise Unauthorized()

    split_val = authorization.split(" ", maxsplit=1)
    if (
        len(split_val) < 2
        or split_val[0] != "Password"
        or split_val[1] != "admin"
    ):
        raise Unauthorized()


app = fastapi.FastAPI()
api = fastapi.APIRouter()
admin_api = fastapi.APIRouter(dependencies=[fastapi.Depends(_is_admin)])


def get_queue_connection():
    with QueueConnection("queue.sqlite") as con:
        con.create()
        yield con


Connection = Annotated[QueueConnection, fastapi.Depends(get_queue_connection)]


@api.get("/ticket/{id}")
def get_ticket(
    id: int,
    connection: Connection,
    token: str | None = None,
) -> QueueTicket:
    if not token:
        raise TicketNotFound()

    ticket = connection.get(id)
    if ticket and ticket.token == token:
        return ticket

    raise TicketNotFound()


@api.post("/tickets", status_code=201)
def new_ticket(new_ticket: NewTicket, connection: Connection) -> QueueTicket:
    return connection.enqueue(new_ticket.name)


def get_token_from_header(val: str) -> str | None:
    split_val = val.split(" ", maxsplit=1)
    if len(split_val) < 2 or split_val[0] != "Token":
        return None

    return split_val[1] or None


@api.delete("/ticket/{id}", status_code=204)
def delete_ticket(
    id: int,
    connection: Connection,
    authorization: OptionalHeader = None,
) -> None:
    token = get_token_from_header(authorization) if authorization else None
    if not token:
        raise fastapi.HTTPException(status_code=401, detail="Unauthorized")

    ticket = connection.get(id)
    if not ticket:
        raise TicketNotFound()

    if ticket.token != token:
        raise Unauthorized()

    connection.remove(id)


@admin_api.get("/tickets")
def get_all_tickets(
    connection: Connection,
    limit: Annotated[int | None, fastapi.Query(min=1)] = None,
) -> list[QueueTicket]:
    return connection.get_all(limit=limit)


@admin_api.get("/ticket/{id}")
def admin_get_ticket(id: int, connection: Connection) -> QueueTicket:
    ticket = connection.get(id)
    if not ticket:
        raise TicketNotFound()

    return ticket


@admin_api.delete("/ticket/{id}", status_code=204)
def admin_delete_ticket(id: int, connection: Connection) -> None:
    connection.remove(id)


api.include_router(admin_api, prefix="/admin")
app.include_router(api, prefix="/api")
