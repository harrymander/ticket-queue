import ipaddress
import logging
import math
import os
import secrets
import socket
import sys
import threading
import time
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

    return PathOrUrl(type=PathOrUrl.Path, value=PACKAGE_DIR)


def get_hostname(host: str) -> str | None:
    if host == "0.0.0.0":
        return socket.gethostname()
    if host in ("127.0.0.1", "::1"):
        return "localhost"
    return None


def get_urls(host: str, port: int) -> list[str]:
    urls = []
    hostname = get_hostname(host)
    if hostname:
        urls.append(f"http://{hostname}:{port}")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if ip.version == 6:
            host = f"[{host}]"

    urls.append(f"http://{host}:{port}")
    return urls


def gen_random_password(nchars: int) -> str:
    return secrets.token_hex(math.ceil(nchars / 2))[:nchars]


DEFAULT_RANDOM_PASSWORD_LEN = 6


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
    help="""Frontend URL(s) to display to user. If not provided, the frontend
    URL will be determined based off the values of --host and --port or
    --frontend if a URL is passed.""",
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
    help="""Auto-reload the server on file change. Use only for dev mode; only
    one worker can be used if enabled.""",
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
    "--random-password-len",
    help=f"""Length of randomly-generated password. Can also be set via the
    RANDOM_PASSWORD_LEN env var. The default length
    ({DEFAULT_RANDOM_PASSWORD_LEN}) is probably not very secure...""",
    default=DEFAULT_RANDOM_PASSWORD_LEN,
    type=click.IntRange(min=1),
    envvar="RANDOM_PASSWORD_LEN",
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
    "--access-logs",
    "access_log_level",
    default="error",
    type=click.Choice(("all", "redirects", "error", "none")),
    help="""HTTP access log level. If "error", only shows error codes (4xx and
    5xx); if "redirects", includes 3xx requests; if "all", includes 2xx
    requests (there will be a lot of these since the frontend regularly polls
    the backend).""",
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
    random_password_len: int,
    browser: bool,
    access_log_level: str,
) -> None:
    if workers > 1 and reload:
        raise click.UsageError("Cannot use --reload with more than one worker")

    if frontend is None:
        frontend = get_packaged_frontend_dir()
        if not frontend:
            raise click.ClickException(
                "No packaged frontend found! "
                "Are you running from a built package? "
                "Either re-build package with frontend, pass an external "
                "frontend path via --frontend, or serve the frontend "
                "separately and and pass the URL via --frontend. "
                "(See --help for more information.)"
            )

    if not database:
        tempdir = ctx.with_resource(TemporaryDirectory(prefix="ticket-queue"))
        database = os.path.join(tempdir, "ticket_queue.db")

    if admin_password is None:
        admin_password = gen_random_password(random_password_len)

    urls = list(urls)
    if frontend.type == PathOrUrl.Path:
        urls.extend(get_urls(host, port))
    else:
        urls.append(frontend.value)
    admin_urls = [f"{u}/admin?password={admin_password}" for u in urls]

    config = Config(
        urls=urls,
        frontend=frontend,
        admin_password=admin_password,
        database=database,
    )
    save_config_to_env(config)
    print_startup_panel(config=config, reload=reload, admin_urls=admin_urls)

    launch_server(
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        access_log_level=access_log_level,
        open_url=admin_urls[0] if browser else None,
    )


def print_startup_panel(
    *,
    config: Config,
    reload: bool,
    admin_urls: Sequence[str],
):
    from rich import print
    from rich.panel import Panel

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
The admin interface is located at:

  {"\n  ".join(admin_urls)}

{password_notice}

Frontend: {config.frontend.value}
Database path: {config.database}
Auto-reload is {'en' if reload else 'dis'}abled
    """.rstrip()

    print(Panel(text, title="Ticket queue"), file=sys.stderr)


class AccessFilter(logging.Filter):
    """Filters out HTTP access logs for successful requests (codes 200-299)
    and redirects (300-399)."""

    def __init__(self, filter_redirects=True):
        self.filter_redirects = filter_redirects
        super().__init__()

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno != logging.INFO:
            return True

        args = record.args
        if not (args and isinstance(args, Sequence)):
            return True

        status = args[-1]
        if not isinstance(status, int):
            return True

        return not (200 <= status < (400 if self.filter_redirects else 300))


def uvicorn_log_config(access_log_level: str) -> dict:
    from uvicorn.config import LOGGING_CONFIG

    conf = LOGGING_CONFIG.copy()
    if access_log_level == "none":
        # The requests are logged on INFO, so still log errors
        conf["loggers"]["uvicorn.access"]["level"] = "ERROR"
    elif access_log_level in ("error", "redirects"):
        conf.setdefault("filters", {})["access_filter"] = {
            "()": "ticket_queue.cli.AccessFilter",
            "filter_redirects": access_log_level == "error",
        }
        conf["handlers"]["access"].setdefault("filters", []).append(
            "access_filter"
        )
    elif access_log_level != "all":
        raise ValueError(f"invalid access_log_level: {access_log_level}")

    return conf


def open_in_browser(url: str) -> None:
    time.sleep(0.5)
    webbrowser.open(url)


def launch_server(
    *,
    host: str,
    port: int,
    workers: int,
    reload: bool,
    access_log_level: str,
    open_url: str | None,
) -> None:
    import uvicorn

    if open_url:
        browser_thread = threading.Thread(
            target=open_in_browser, args=(open_url,)
        )
        browser_thread.start()
    else:
        browser_thread = None

    try:
        uvicorn.run(
            "ticket_queue.app:create_app",
            host=host,
            port=port,
            workers=workers,
            reload=reload,
            factory=True,
            log_config=uvicorn_log_config(access_log_level),
        )
    finally:
        if browser_thread:
            browser_thread.join()
