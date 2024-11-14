from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response


class StaticFilesSPA(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        try:
            response = await super().get_response(path, scope)
        except HTTPException:
            response = await super().get_response(".", scope)

        return response


def create_app() -> FastAPI:
    from ticket_queue.api import api
    from ticket_queue.config import get_config, load_config_from_env
    from ticket_queue.ticket_queue import QueueConnection

    load_config_from_env()
    config = get_config()
    with QueueConnection(config.database) as q:
        q.create()

    app = FastAPI(openapi_url=None)
    app.mount("/api", api)
    if config.frontend:
        static_router = StaticFilesSPA(directory=config.frontend, html=True)
        app.mount("/", static_router)

    return app
