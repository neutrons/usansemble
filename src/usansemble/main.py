"""Command-line entry point that starts the usansemble NiceGUI server.

Run it with ``pixi run start``, ``usansemble`` (the installed console script), or
``python -m usansemble.main``. A sign-in to ONCat is required to fetch runs, so a
``storage_secret`` is supplied to persist the per-browser token across restarts.
"""

import argparse

import argcomplete
from nicegui import ui

# pyoncatng owns the ONCat login configuration; ensure its config file exists and
# carries the latest [login.oncat] defaults so the login widget finds a client ID.
from pyoncatng.configuration import Configuration

# Registers the ``@ui.page`` routes as a side effect of import.
from usansemble import app  # noqa: F401

# Dev-only secret so ``app.storage.user`` (per-browser token persistence) works
# out of the box. For any real deployment pass your own via --storage-secret.
_DEFAULT_STORAGE_SECRET = "usansemble-dev-secret-change-me"  # noqa: S105


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="usansemble", description="Run the usansemble web app.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8080, help="Port to serve on (default: 8080).")
    parser.add_argument(
        "--storage-secret",
        default=_DEFAULT_STORAGE_SECRET,
        help="Secret used to sign per-user storage cookies.",
    )
    parser.add_argument(
        "--native",
        action="store_true",
        help="Open in a native desktop window instead of a browser tab.",
    )
    return parser


def main() -> None:
    """Parse arguments (with shell completion) and start the NiceGUI server."""
    parser = _build_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    # Ensure ~/.pyoncatng/configuration.ini exists and carries the latest
    # [login.oncat] defaults (created/backfilled from the bundled template).
    Configuration()
    ui.run(
        host=args.host,
        port=args.port,
        storage_secret=args.storage_secret,
        native=args.native,
        reload=False,
        title="usansemble",
    )


# ``ui.run`` must be reached at import time for NiceGUI's launcher; guard so the
# module can still be imported without starting a server.
if __name__ in {"__main__", "__mp_main__"}:
    main()
