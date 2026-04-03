"""
GhostGrid — pyngrok Tunnel Launcher  (Phase 05)
=================================================

Hackathon handoff helper.  Run this script instead of invoking uvicorn
directly and you immediately get a public HTTPS URL you can paste into
Slack / WhatsApp for your teammate — no Docker, no port-forwarding,
no firewall rules.

What this script does
---------------------
1.  Validates that the model directory exists (fast-fail before binding a port).
2.  Spawns the FastAPI server in a subprocess:
        uvicorn src.api_server:app --host 0.0.0.0 --port 8000
3.  Waits until the server is actually accepting connections on :8000.
4.  Opens a pyngrok HTTP tunnel → port 8000.
5.  Prints the public URL prominently.
6.  Blocks until Ctrl-C, then shuts down the tunnel and the subprocess cleanly.

Usage
-----
    python src/start_server.py

    # With a custom ngrok authtoken (first time only — token is cached):
    NGROK_AUTHTOKEN=<your_token> python src/start_server.py

    # Or set it permanently:
    ngrok config add-authtoken <your_token>

Environment Variables
---------------------
NGROK_AUTHTOKEN  Optional. ngrok authentication token for longer session limits.
                 Without it pyngrok uses an anonymous tunnel (limited bandwidth).
GG_PORT          Optional. Override the default port (8000).
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time

# pyngrok — installed via:  pip install pyngrok
try:
    from pyngrok import conf as ngrok_conf
    from pyngrok import ngrok
    from pyngrok.exception import PyngrokError
except ImportError:
    print(
        "\n[GhostGrid] pyngrok is not installed.\n"
        "  Run:  pip install pyngrok\n"
        "  Or:   pip install -r requirements.txt\n"
    )
    sys.exit(1)

import pathlib

# ── Configuration ─────────────────────────────────────────────────────────────
_ROOT      : pathlib.Path = pathlib.Path(__file__).resolve().parents[1]
_MODEL_DIR : pathlib.Path = _ROOT / "models" / "ghostgrid_mbert"
_PORT      : int          = int(os.getenv("GG_PORT", "8000"))
_HOST      : str          = "0.0.0.0"
_POLL_INTERVAL : float    = 0.5   # seconds between readiness polls
_STARTUP_TIMEOUT: float   = 120.0 # max seconds to wait for uvicorn to bind

# ANSI colours (disabled on non-TTY)
_BOLD   = "\033[1m"  if sys.stdout.isatty() else ""
_CYAN   = "\033[96m" if sys.stdout.isatty() else ""
_GREEN  = "\033[92m" if sys.stdout.isatty() else ""
_YELLOW = "\033[93m" if sys.stdout.isatty() else ""
_RED    = "\033[91m" if sys.stdout.isatty() else ""
_GRAY   = "\033[90m" if sys.stdout.isatty() else ""
_RESET  = "\033[0m"  if sys.stdout.isatty() else ""

_SEP = _GRAY + "─" * 72 + _RESET


def _banner(msg: str) -> None:
    print(f"\n{_BOLD}{_CYAN}{msg}{_RESET}")


def _ok(msg: str) -> None:
    print(f"  {_GREEN}✓{_RESET}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {_YELLOW}⚠{_RESET}  {msg}")


def _err(msg: str) -> None:
    print(f"  {_RED}✗{_RESET}  {msg}")


def _wait_for_port(host: str, port: int, timeout: float) -> bool:
    """Poll until TCP port is open or timeout expires. Returns True on success."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(_POLL_INTERVAL)
    return False


# ── Step 0 — Fast-fail guard ───────────────────────────────────────────────────
def _check_model_dir() -> None:
    if not _MODEL_DIR.exists():
        _err(f"Model directory not found: {_MODEL_DIR}")
        print(
            "       Run `python src/train_mbert.py` first to produce "
            "fine-tuned weights.\n"
        )
        sys.exit(1)
    _ok(f"Model directory found: {_MODEL_DIR.relative_to(_ROOT)}")


# ── Step 1 — Launch uvicorn subprocess ────────────────────────────────────────
def _launch_uvicorn() -> subprocess.Popen:
    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.api_server:app",
        "--host", _HOST,
        "--port", str(_PORT),
    ]
    _ok(f"Spawning uvicorn:  {' '.join(cmd)}")
    # Inherit stdout/stderr so the server's logs stream directly to this console
    proc = subprocess.Popen(cmd, cwd=str(_ROOT))
    return proc


# ── Step 2 — Wait for server readiness ────────────────────────────────────────
def _await_server() -> None:
    print(f"  {_GRAY}…{_RESET}  Waiting for uvicorn to bind on :{_PORT} "
          f"(timeout {_STARTUP_TIMEOUT:.0f}s) …", end="", flush=True)
    ready = _wait_for_port("127.0.0.1", _PORT, _STARTUP_TIMEOUT)
    print()  # newline after the waiting dots
    if not ready:
        _err(
            f"uvicorn did not start within {_STARTUP_TIMEOUT:.0f}s. "
            "Check the logs above for errors."
        )
        sys.exit(1)
    _ok(f"Server is accepting connections on port {_PORT}.")


# ── Step 3 — Open pyngrok tunnel ──────────────────────────────────────────────
def _open_tunnel() -> str:
    """Open an HTTP tunnel and return the public HTTPS URL."""
    authtoken = os.getenv("NGROK_AUTHTOKEN")
    if authtoken:
        ngrok_conf.get_default().auth_token = authtoken
        _ok("ngrok authtoken loaded from NGROK_AUTHTOKEN env-var.")
    else:
        _warn(
            "NGROK_AUTHTOKEN not set — using anonymous tunnel "
            "(bandwidth-limited, session expires ~2 h)."
        )
        _warn(
            "Get a free token at https://dashboard.ngrok.com/get-started/your-authtoken "
            "then re-run with:  NGROK_AUTHTOKEN=<token> python src/start_server.py"
        )

    http_tunnel = ngrok.connect(addr=_PORT, proto="http")
    public_url: str = http_tunnel.public_url  # type: ignore[union-attr]

    # ngrok always returns http:// for free tunnels but also serves HTTPS
    https_url = public_url.replace("http://", "https://", 1)
    return https_url


# ── Step 4 — Print handoff block ──────────────────────────────────────────────
def _print_handoff(public_url: str) -> None:
    predict_url = f"{public_url}/v1/predict"
    docs_url    = f"{public_url}/docs"

    print()
    print(_SEP)
    print(f"  {_BOLD}{_GREEN}🚀  GhostGrid API is LIVE{_RESET}")
    print(_SEP)
    print(f"  {_BOLD}Public URL       {_RESET}→  {_CYAN}{public_url}{_RESET}")
    print(f"  {_BOLD}Predict Endpoint {_RESET}→  {_CYAN}{predict_url}{_RESET}")
    print(f"  {_BOLD}Swagger / Docs   {_RESET}→  {_CYAN}{docs_url}{_RESET}")
    print(_SEP)
    print(
        f"  {_YELLOW}Share the Public URL above with your teammate.{_RESET}\n"
        f"  {_GRAY}Press Ctrl-C to stop the server and close the tunnel.{_RESET}"
    )
    print(_SEP)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    _banner("━━━  GhostGrid  ·  pyngrok Tunnel Launcher (Phase 05)  ━━━")
    print(_SEP)

    # 0. Guard
    _check_model_dir()

    # 1. Spawn uvicorn
    proc = _launch_uvicorn()

    # Register cleanup so Ctrl-C always kills the child process
    def _shutdown(signum=None, frame=None) -> None:  # type: ignore[assignment]
        print(f"\n{_YELLOW}[GhostGrid] Shutting down …{_RESET}")
        ngrok.kill()
        _ok("ngrok tunnel closed.")
        if proc.poll() is None:        # still running
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        _ok("uvicorn process stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # 2. Wait until server is ready
    try:
        _await_server()
    except SystemExit:
        _shutdown()

    # 3. Open tunnel
    try:
        public_url = _open_tunnel()
    except PyngrokError as exc:
        _err(f"pyngrok failed to open tunnel: {exc}")
        _shutdown()
        return   # unreachable but satisfies type checkers

    # 4. Print handoff info
    _print_handoff(public_url)

    # 5. Block until Ctrl-C
    try:
        proc.wait()           # blocks until the uvicorn process exits
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()
