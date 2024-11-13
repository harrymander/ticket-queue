import base64
import binascii
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Path,
    Query,
)

from ticket_queue.models import NewTicket, QueueTicket
from ticket_queue.ticket_queue import QueueConnection


class TicketNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="Ticket not found")


class Unauthorized(HTTPException):
    def __init__(self):
        super().__init__(status_code=401, detail="Unauthorized")


PasswordAuthHeader = Annotated[
    str | None,
    Header(
        description=(
            "Authentication header with format "
            "`Password <base64-encoded password>`"
        )
    ),
]


def base64_decode(val: str) -> str | None:
    try:
        decoded = base64.b64decode(val, validate=True)
    except binascii.Error:
        return None

    try:
        return decoded.decode()
    except UnicodeDecodeError:
        return None


def _is_admin(authorization: PasswordAuthHeader = None):
    if not authorization:
        raise Unauthorized()

    name, *val = authorization.split(" ", maxsplit=1)
    if not val or name != "Password":
        raise Unauthorized()

    password = base64_decode(val[0])
    if password != "admin":
        raise Unauthorized()


app = FastAPI()
api = APIRouter()
admin_api = APIRouter(dependencies=[Depends(_is_admin)])


def get_queue_connection():
    with QueueConnection("queue.sqlite") as con:
        con.create()
        yield con


Connection = Annotated[QueueConnection, Depends(get_queue_connection)]
TicketId = Annotated[int, Path(description="Ticket ID")]
TokenQuery = Annotated[str, Query(description="Ticket token")]


@api.get("/ticket/{id}")
def get_ticket(
    id: TicketId,
    connection: Connection,
    token: TokenQuery,
) -> QueueTicket:
    """Get a ticket by ID and token.

    Returns 404 if ticket is not found or the provided token does not match.
    """

    ticket = connection.get(id)
    if ticket and ticket.token == token:
        return ticket

    raise TicketNotFound()


@api.post("/tickets", status_code=201)
def new_ticket(new_ticket: NewTicket, connection: Connection) -> QueueTicket:
    return connection.enqueue(new_ticket.name)


TokenAuthHeader = Annotated[
    str,
    Header(
        description=(
            "Authorization header containing token for ticket. "
            "Has format `Token <token>`"
        )
    ),
]


def get_token_from_header(authorization: TokenAuthHeader) -> str:
    name, *val = authorization.split(" ", maxsplit=1)
    if not val or name != "Token":
        raise Unauthorized()
    return val[0]


TicketToken = Annotated[str, Depends(get_token_from_header)]


@api.delete("/ticket/{id}", status_code=204)
def delete_ticket(
    id: TicketId,
    connection: Connection,
    token: TicketToken,
) -> None:
    ticket = connection.get(id)
    if not ticket:
        raise TicketNotFound()

    if ticket.token != token:
        raise Unauthorized()

    connection.remove(id)


@admin_api.get("/tickets")
def get_all_tickets(
    connection: Connection,
    limit: Annotated[int | None, Query(min=1)] = None,
) -> list[QueueTicket]:
    return connection.get_all(limit=limit)


@admin_api.get("/ticket/{id}")
def admin_get_ticket(id: TicketId, connection: Connection) -> QueueTicket:
    ticket = connection.get(id)
    if not ticket:
        raise TicketNotFound()

    return ticket


@admin_api.delete("/ticket/{id}", status_code=204)
def admin_delete_ticket(id: TicketId, connection: Connection) -> None:
    connection.remove(id)


api.include_router(admin_api, prefix="/admin")
app.include_router(api, prefix="/api")
