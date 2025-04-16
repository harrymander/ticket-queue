# Ticket queue

## Development

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) for
Python dependency management. Node dependencies must be installed manually:

```
cd frontend && npm install
```

To run a dev server (requires tmux):

```
make dev
```

This will start the backend and frontend dev servers in separate tmux windows.
To run the dev servers separately, run `make dev-frontend` and
`make dev-backend` in separate terminals. Run `make help` for a full list of
commands.
