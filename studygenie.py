"""StudyGenie – AI Study Companion.

    python studygenie.py          opens the desktop window
    python studygenie.py --web    serves it to browsers, including phones
                                  and tablets on the same Wi-Fi

The code lives in app/ (one file per page in app/views/), the tests in
tests/ (python -m unittest). Your data is saved in studygenie_data.db.

Setup: see requirements.txt (installs into the project's .venv), then
`ollama pull gemma3:4b`. Or open the folder in the Dev Container
(.devcontainer/), run it with --web --no-browser and open
http://localhost:8550.
"""

import argparse
import os
import socket

import flet as ft

from app.main import main


def lan_address():
    """This computer's address on the local network, for phones to open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("10.255.255.255", 1))  # no traffic is sent; this just picks the right interface
            return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StudyGenie – AI Study Companion")
    parser.add_argument("--web", action="store_true", help="serve in the browser (phones, tablets, other computers)")
    parser.add_argument("--port", type=int, default=8550)
    parser.add_argument("--local-only", action="store_true", help="with --web: only this computer can connect")
    parser.add_argument("--no-browser", action="store_true", help="with --web: don't open a browser tab")
    args = parser.parse_args()

    if args.web:
        host = "127.0.0.1" if args.local_only else "0.0.0.0"
        if args.no_browser:
            os.environ["FLET_FORCE_WEB_SERVER"] = "1"
        print(f"StudyGenie is running at http://127.0.0.1:{args.port}")
        if not args.local_only:
            print(f"On a phone or tablet on the same Wi-Fi, open http://{lan_address()}:{args.port}")
        ft.run(main, view=ft.AppView.WEB_BROWSER, host=host, port=args.port)
    else:
        ft.run(main)
