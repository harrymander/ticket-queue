from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response

from ticket_queue.config import PathOrUrl


class StaticFilesSPA(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        try:
            response = await super().get_response(path, scope)
        except HTTPException:
            response = await super().get_response(".", scope)

        return response


def configure_frontend(app: FastAPI, frontend: PathOrUrl) -> None:
    if frontend.type == PathOrUrl.Url:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[frontend.value],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.mount("/", StaticFilesSPA(directory=frontend.value, html=True))


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
    configure_frontend(app, config.frontend)
    return app
