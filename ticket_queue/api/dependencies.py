from typing import Annotated

from fastapi import Depends, Path, Query

from ticket_queue.config import Config, get_config
from ticket_queue.ticket_queue import QueueConnection

AppConfig = Annotated[Config, Depends(get_config)]


def get_queue_connection(config: AppConfig):
    with QueueConnection(config.database) as con:
        yield con


Connection = Annotated[QueueConnection, Depends(get_queue_connection)]
TicketId = Annotated[int, Path(description="Ticket ID")]
TokenQuery = Annotated[str, Query(description="Ticket token")]
