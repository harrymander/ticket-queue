# Ticket queue

## Quick start

This project is not currently available on PyPI. However, the server can be run
directly without cloning using a package manager such as `uvx` or `pipx`:

```
uvx git+https://github.com/harrymander/ticket-queue.git
```

By default this will open a browser window to the admin page. To persist the
queue database to a file, pass `--database=path/to/db`. Pass `--help` for a
complete list of options.

### Manual installation

Clone this directory and create a virtualenv. Then install the
project to the virtualenv:

```
pip install .
```

Then run `ticket-queue` directly. (Note you can install the project directly
to your global Python environment without using a virtualenv, but this is
not recommended since it may break your system Python installation.)

## Development

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) for
Python dependency management. Node dependencies must be installed manually:

```
npm -C frontend install
```

To run a dev server (requires tmux):

```
make dev
```

This will start the backend and frontend dev servers in separate tmux windows.
To run the dev servers separately, run `make dev-frontend` and
`make dev-backend` in separate terminals. Run `make help` for a full list of
commands.
