import base64
import binascii
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from ticket_queue.api.dependencies import AppConfig, QueueConnector, TicketId
from ticket_queue.api.errors import TicketNotFound, Unauthorized
from ticket_queue.models import QueueTicket

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


def is_admin(config: AppConfig, authorization: PasswordAuthHeader = None):
    if not authorization:
        raise Unauthorized()

    name, *val = authorization.split(" ", maxsplit=1)
    if not val or name != "Password":
        raise Unauthorized()

    password = base64_decode(val[0])
    if password != config.admin_password:
        raise Unauthorized()


admin_api = APIRouter(dependencies=[Depends(is_admin)])


@admin_api.get("/tickets")
def get_all_tickets(
    connector: QueueConnector,
    limit: Annotated[int | None, Query(min=1)] = None,
) -> list[QueueTicket]:
    with connector as queue:
        return queue.get_all(limit=limit)


@admin_api.get("/ticket/{id}")
def admin_get_ticket(id: TicketId, connector: QueueConnector) -> QueueTicket:
    with connector as queue:
        ticket = queue.get(id)
    if not ticket:
        raise TicketNotFound()

    return ticket


@admin_api.delete("/ticket/{id}", status_code=204)
def admin_delete_ticket(id: TicketId, connector: QueueConnector) -> None:
    with connector as queue:
        queue.remove(id)
