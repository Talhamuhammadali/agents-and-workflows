"""secrets-viewer: a tiny store-agnostic demo app for the migration scenario.

The app never talks to AWS or Vault directly. It reads whatever secret files
are mounted into SECRETS_DIR and displays them. Everything behind that mount
(AWS Secrets Manager here, HashiCorp Vault on the migrated target) is what the
migration actually swaps; the app is the invariant.

Routes
------
/         HTML page listing every mounted secret (the UI).
/secrets  JSON API: {app_env, count, secrets}.
/healthz  Liveness/readiness + ALB health check.
"""

import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SECRETS_DIR = os.environ.get("SECRETS_DIR", "/etc/app-secrets")
APP_ENV = os.environ.get("APP_ENV", "unknown")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "info")
PORT = int(os.environ.get("PORT", "8080"))


def read_secrets() -> dict:
    """Return every secret mounted into SECRETS_DIR as a name to value map.

    Returns
    -------
    dict
        Mapping of secret name to its string value. Empty when the mount is
        absent, which is itself a useful signal that syncing has not happened.
    """
    secrets = {}
    if not os.path.isdir(SECRETS_DIR):
        return secrets
    for name in sorted(os.listdir(SECRETS_DIR)):
        path = os.path.join(SECRETS_DIR, name)
        if os.path.isfile(path):
            with open(path) as handle:
                secrets[name] = handle.read().strip()
    return secrets


def render_page(secrets: dict) -> bytes:
    """Render the HTML UI listing the mounted secrets.

    Parameters
    ----------
    secrets
        The name to value map to display.

    Returns
    -------
    bytes
        A complete HTML document.
    """
    if secrets:
        rows = "".join(
            f"<tr><td class=k>{html.escape(name)}</td>"
            f"<td class=v><code>{html.escape(value)}</code></td></tr>"
            for name, value in secrets.items()
        )
    else:
        rows = "<tr><td colspan=2 class=empty>no secrets mounted &mdash; sync has not happened yet</td></tr>"

    doc = f"""<!doctype html>
<html lang=en>
<meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>secrets-viewer</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, sans-serif; max-width: 760px; margin: 3rem auto; padding: 0 1rem; }}
  h1 {{ margin-bottom: .25rem; }}
  .badge {{ display:inline-block; padding:.15rem .6rem; border-radius:999px; background:#2563eb; color:#fff; font-size:.8rem; }}
  table {{ width:100%; border-collapse:collapse; margin-top:1.5rem; }}
  th, td {{ text-align:left; padding:.6rem .5rem; border-bottom:1px solid #8883; }}
  th {{ font-size:.75rem; text-transform:uppercase; letter-spacing:.05em; opacity:.7; }}
  td.k {{ font-weight:600; white-space:nowrap; }}
  td.v code {{ background:#8882; padding:.15rem .4rem; border-radius:4px; }}
  .empty {{ text-align:center; opacity:.6; padding:2rem; }}
  footer {{ margin-top:2rem; font-size:.8rem; opacity:.6; }}
</style>
<h1>secrets-viewer</h1>
<p>source: <span class=badge>{html.escape(APP_ENV)}</span> &nbsp; {len(secrets)} secret(s) mounted from <code>{html.escape(SECRETS_DIR)}</code></p>
<table>
  <thead><tr><th>name</th><th>value</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<footer>JSON at <a href="/secrets">/secrets</a> &middot; health at <a href="/healthz">/healthz</a></footer>
</html>"""
    return doc.encode()


class Handler(BaseHTTPRequestHandler):
    """Minimal router for the UI, the JSON API, and the health endpoint."""

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload, indent=2).encode(), "application/json")

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._json(200, {"ok": True})
        elif self.path == "/secrets":
            secrets = read_secrets()
            self._json(200, {"app_env": APP_ENV, "count": len(secrets), "secrets": secrets})
        elif self.path == "/":
            self._send(200, render_page(read_secrets()), "text/html; charset=utf-8")
        else:
            self._json(404, {"error": "not found", "path": self.path})

    def log_message(self, fmt: str, *args) -> None:
        if LOG_LEVEL == "debug":
            super().log_message(fmt, *args)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"secrets-viewer listening on :{PORT} env={APP_ENV} secrets_dir={SECRETS_DIR}", flush=True)
    server.serve_forever()
