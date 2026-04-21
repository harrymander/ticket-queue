# Ticket queue

A simple ticket queue web app that can be run from a single command.

## Contents

1. [Quick start](#quick-start)
2. [Security warning](#security-warning)
3. [Development](#development)

## Quick start

### Python package manager

This project is not currently available on PyPI. However, the server can be run
directly without cloning using a package manager such as `uvx` or `pipx`:

```
uvx git+https://github.com/harrymander/ticket-queue.git@bundled
```

By default this will open a browser window to the admin page. To persist the
queue database to a file, pass `--database=path/to/db`. Pass `--help` for a
complete list of options.

The `bundled` branch (specified via `@bundled` in the above command) contains a
pre-built copy of the frontend, so the server can be run without Node.js being
installed. This branch is automatically updated by GitHub Actions whenever
`main` is updated. If you have Node.js installed and want to build the frontend
yourself (e.g. if you want to use a different version of node), run the above
command without the `@bundled` suffix.

### Docker

You can also run the published container image from GitHub Container Registry:

```
docker run --rm --network host ghcr.io/harrymander/ticket-queue:latest
```

If you don't want to run in host network mode, specify the port and URL
manually. E.g.:

```
docker run --rm -p 8000:8000 ghcr.io/harrymander/ticket-queue:latest --url=<CLIENT DISPLAY URL>
```

### Manual installation

Clone this directory and create a virtualenv. Then install the
project to the virtualenv:

```
pip install .
```

Then run `ticket-queue` directly. (Note you can install the project directly
to your global Python environment without using a virtualenv, but this is
not recommended since it may break your system Python installation.)

**Note:** Node.js must also be installed to build the package on the `main`
branch. Check out the `bundled` branch to use the pre-packaged frontend if Node
is not installed.

## Security warning

This project is intended for lightweight, self-hosted use. It should not be used
in any important or large-scale applications.

- Admin passwords and client tokens are persisted in plain text in client-side
  localStorage.
- Admin URLs can include the password as a query parameter, which can leak via
  logs, history, and screenshots.
- Client tokens are stored in plain text in the database.

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
