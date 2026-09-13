#!/usr/bin/env python3
"""Local launcher for Wiki Hami Extraction V1.

Examples:
    python run.py --api
    python run.py --api --reload
    python run.py --web
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _environment() -> dict[str, str]:
    """Return an environment where repository packages are importable."""
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    root = str(ROOT)
    env["PYTHONPATH"] = root if not current else f"{root}{os.pathsep}{current}"
    return env


def _exec(args: list[str]) -> None:
    """Replace this launcher with the requested server process."""
    os.chdir(ROOT)
    os.execvpe(sys.executable, [sys.executable, *args], _environment())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Wiki Hami Extraction V1 locally.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--api", action="store_true", help="Run the FastAPI service.")
    mode.add_argument("--web", action="store_true", help="Run the Streamlit inspector.")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address for the selected service (default: 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Override the default port (API: 8000, web: 8501).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable Uvicorn auto-reload in API mode.",
    )
    args = parser.parse_args()

    if args.web and args.reload:
        parser.error("--reload is only valid with --api")

    if args.api:
        port = args.port or 8000
        command = [
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            args.host,
            "--port",
            str(port),
        ]
        if args.reload:
            command.append("--reload")
        _exec(command)

    port = args.port or 8501
    _exec(
        [
            "-m",
            "streamlit",
            "run",
            str(ROOT / "ui" / "streamlit_app.py"),
            "--server.address",
            args.host,
            "--server.port",
            str(port),
        ]
    )


if __name__ == "__main__":
    main()
