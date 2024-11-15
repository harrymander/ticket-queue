from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response

from ticket_queue.config import (
    Config,
    PathOrUrl,
    get_config,
    load_config_from_env,
)
from ticket_queue.ticket_queue import QueueConnection


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


def _create_app(config: Config) -> FastAPI:
    from ticket_queue.api import api

    with QueueConnection(config.database) as queue:
        queue.create()

    app = FastAPI(openapi_url=None)
    app.mount("/api", api)
    configure_frontend(app, config.frontend)
    return app


def create_app() -> FastAPI:
    load_config_from_env()
    return _create_app(get_config())
