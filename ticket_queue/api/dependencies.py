from typing import Annotated

from fastapi import Depends, Path, Query

from ticket_queue.config import Config, get_config
from ticket_queue.ticket_queue import QueueConnection

AppConfig = Annotated[Config, Depends(get_config)]


class _QueueConnector:
    """
    A factory class for creating a connection to the queue database.

    Usage:

        connector = _QueueConnector(db_path)
        with connector as connection:
            # Do stuff with connection, will be closed automatically on exit
            # from context

    TODO: This is pretty hacky... it is needed because it seems that
    FastAPI/Starlette/uvicorn will sometimes initialise dependencies in a
    different thread than the request handler, so an SQLite exception is raised
    due to using a connection being used in a different thread to the one it
    was created in (SQLite connections are not thread-safe).
    """

    def __init__(self, config: AppConfig):
        self.db_path = config.database

    def __enter__(self) -> QueueConnection:
        self._connection = QueueConnection(self.db_path)
        return self._connection

    def __exit__(self, *_):
        self._connection.close()


QueueConnector = Annotated[_QueueConnector, Depends()]
TicketId = Annotated[int, Path(description="Ticket ID")]
TokenQuery = Annotated[str, Query(description="Ticket token")]
