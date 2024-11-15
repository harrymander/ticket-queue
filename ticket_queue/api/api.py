from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    Header,
)

from ticket_queue.api.admin_api import admin_api
from ticket_queue.api.dependencies import QueueConnector, TicketId, TokenQuery
from ticket_queue.api.errors import TicketNotFound, Unauthorized
from ticket_queue.models import NewTicket, QueueTicket


def _create_api() -> FastAPI:
    from ticket_queue.config import get_config

    kw: dict = {}
    if not get_config().enable_api_docs:
        kw["openapi_url"] = None
        kw["docs_url"] = None
        kw["redoc_url"] = None

    return FastAPI(**kw)


api = _create_api()


@api.get("/ticket/{id}")
def get_ticket(
    id: TicketId,
    connector: QueueConnector,
    token: TokenQuery,
) -> QueueTicket:
    """Get a ticket by ID and token.

    Returns 404 if ticket is not found or the provided token does not match.
    """

    with connector as queue:
        ticket = queue.get(id)
    if ticket and ticket.token == token:
        return ticket

    raise TicketNotFound()


@api.post("/tickets", status_code=201)
def new_ticket(
    new_ticket: NewTicket, connector: QueueConnector
) -> QueueTicket:
    with connector as queue:
        return queue.enqueue(new_ticket.name)


TokenAuthHeader = Annotated[
    str | None,
    Header(
        description=(
            "Authorization header containing token for ticket. "
            "Has format `Token <token>`"
        )
    ),
]


def get_token_from_header(authorization: TokenAuthHeader = None) -> str:
    if not authorization:
        raise Unauthorized()
    name, *val = authorization.split(" ", maxsplit=1)
    if not val or name != "Token":
        raise Unauthorized()
    return val[0]


TicketToken = Annotated[str, Depends(get_token_from_header)]


@api.delete("/ticket/{id}", status_code=204)
def delete_ticket(
    id: TicketId,
    connector: QueueConnector,
    token: TicketToken,
) -> None:
    with connector as queue:
        ticket = queue.get(id)
        if not ticket:
            raise TicketNotFound()

        if ticket.token != token:
            raise Unauthorized()

        queue.remove(id)


api.include_router(admin_api, prefix="/admin")
