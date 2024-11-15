import os
import secrets
import socket
import webbrowser
from collections.abc import Sequence
from tempfile import TemporaryDirectory
from typing import cast

import click

from ticket_queue.config import Config, PathOrUrl, is_url, save_config_to_env


class DirPathOrUrl(click.Path):
    name = "PATH | URL"

    def __init__(self):
        super().__init__(
            file_okay=False,
            dir_okay=True,
            exists=True,
            readable=True,
            writable=True,
        )

    # (Ignores the incompatible return type error)
    def convert(self, value, param, ctx) -> PathOrUrl:  # type: ignore
        if is_url(value):
            return PathOrUrl(type=PathOrUrl.Url, value=value)

        path = super().convert(value, param, ctx)
        return PathOrUrl(type=PathOrUrl.Path, value=cast(str, path))


class WritableFilePath(click.Path):
    def __init__(self):
        super().__init__(
            file_okay=True,
            dir_okay=False,
            writable=True,
            readable=True,
        )

    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        parent = os.path.dirname(value)
        if parent:
            if not os.path.exists(parent):
                self.fail(f"Parent path '{parent}' does not exist")
            if not os.path.isdir(parent):
                self.fail(f"Parent path '{parent}' is not a directory")

        return value


def get_packaged_frontend_dir() -> PathOrUrl | None:
    try:
        from ticket_queue._packaged_frontend import PACKAGE_DIR
    except ImportError:
        return None

    if not os.path.isdir(PACKAGE_DIR):
        return None

    return PathOrUrl(type=PathOrUrl.Path, value="PACKAGE_DIR")


def get_hostname(host: str) -> str | None:
    if host in ("0.0.0.0", "::"):
        return socket.gethostname()
    if host in ("127.0.0.1", "::1"):
        return "localhost"
    return None


def get_urls(host: str, port: int) -> list[str]:
    urls = []
    hostname = get_hostname(host)
    if hostname:
        urls.append(f"http://{hostname}:{port}")
    urls.append(f"http://{host}:{port}")
    return urls


def gen_random_password(nbytes: int) -> str:
    return secrets.token_hex(nbytes)


@click.command(context_settings={"show_default": True})
@click.option("--host", default="0.0.0.0")
@click.option(
    "--port",
    "-p",
    type=click.IntRange(min=1, max=0xFFFF),
    default=8000,
)
@click.option(
    "--url",
    "urls",
    help="""Frontend URL(s) to display to user. Automatically set off value of
    --host and --port or --frontend if it is a URL.""",
    multiple=True,
)
@click.option(
    "--workers",
    help="Number of workers.",
    default=1,
    type=click.IntRange(min=1),
)
@click.option(
    "--reload/--no-reload",
    default=False,
    help="Auto-reload the server on file change. Use only for dev mode.",
)
@click.option(
    "--frontend",
    type=DirPathOrUrl(),
    help="""Path to frontend directory or a URL from which the frontend is
    being served. If not provided, will serve the bundled frontend. Note that
    if a URL is provided, the user is responsible for serving it separately
    (the URL is required by this app for configuring CORS).""",
)
@click.option(
    "--admin-password",
    help="""Password for the admin interface. If not provided, a password is
    randomly generated.""",
)
@click.option(
    "--random-password-bytes",
    help="""Number of bytes to generate password. Can also be set via the
    RAND_PASSWORD_BYTES env var.""",
    default=3,
    type=click.IntRange(min=1),
    envvar="RAND_PASSWORD_BYTES",
)
@click.option(
    "--database",
    "--db",
    type=WritableFilePath(),
    help="""Path to SQLite database file. If not provided, uses a temporary
    file that is deleted when the server exits.""",
)
@click.option(
    "--browser/--no-browser",
    default=True,
    help="Automatically open a browser window to the admin page.",
)
@click.option(
    "--api-docs/--no-api-docs",
    default=True,
    help="""Enable the API documentation under /api/docs.""",
)
@click.pass_context
def cli(
    ctx: click.Context,
    host: str,
    port: int,
    urls: Sequence[str],
    workers: int,
    reload: bool,
    frontend: PathOrUrl | None,
    admin_password: str | None,
    database: str | None,
    random_password_bytes: int,
    browser: bool,
    api_docs: bool,
) -> None:
    if workers > 1 and reload:
        raise click.UsageError("Cannot use --reload with more than one worker")

    if frontend is None:
        frontend = get_packaged_frontend_dir()
        if not frontend:
            raise click.ClickException(
                "No packaged frontend found! "
                "Are you running from a built package? "
                "Either re-build package with frontend, serve the frontend "
                "separately and pass --no-frontend, or provide a path to the "
                "frontend with --frontend."
            )

    urls = list(urls)
    if frontend.type == PathOrUrl.Path:
        urls.extend(get_urls(host, port))
    else:
        urls.append(frontend.value)

    if not database:
        tempdir = ctx.with_resource(TemporaryDirectory(prefix="ticket-queue"))
        database = os.path.join(tempdir, "ticket_queue.db")

    if not admin_password:
        admin_password = gen_random_password(random_password_bytes)

    config = Config(
        urls=urls,
        frontend=frontend,
        admin_password=admin_password,
        database=database,
        enable_api_docs=api_docs,
    )
    save_config_to_env(config)
    print_startup_panel(config=config, reload=reload)

    if browser:
        webbrowser.open(f"{urls[0]}/admin")

    launch_server(
        host=host,
        port=port,
        workers=workers,
        reload=reload,
    )


def enabled_str(enabled: bool) -> str:
    return "enabled" if enabled else "disabled"


def print_startup_panel(*, config: Config, reload: bool):
    from rich import print
    from rich.panel import Panel

    admin_urls = "\n  ".join(f"{u}/admin" for u in config.urls)
    if config.admin_password:
        password_notice = (
            "Admin password: "
            f"[black on yellow]{config.admin_password}[/black on yellow]"
        )
    else:
        password_notice = (
            "[bold red]Warning: there is no admin password![/bold red]"
        )

    text = f"""\
The admin interface is located is available at:

  {admin_urls}

{password_notice}

Frontend: {config.frontend.value}
Database path: {config.database}
Auto-reload is {enabled_str(reload)}
API docs are {enabled_str(config.enable_api_docs)}
    """.rstrip()

    print(Panel(text, title="Ticket queue"))


def launch_server(
    *,
    host: str,
    port: int,
    workers: int,
    reload: bool,
) -> None:
    import uvicorn

    uvicorn.run(
        "ticket_queue.app:create_app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        factory=True,
    )
