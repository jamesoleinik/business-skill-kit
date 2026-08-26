"""Interactive sign-in helper for a Dataverse MCP endpoint (standard library only).

Runs the OAuth 2.0 authorization-code + PKCE flow against Microsoft Entra as a public
client, opening the system browser for an interactive sign-in and capturing the redirect on
a loopback address. It writes the resulting access token and refresh token to a local file so
other tooling (the live harness, a raw MCP client) can call the MCP endpoint without a fresh
sign-in every run. Refreshing is handled by --refresh.

This helper hardcodes no environment: authority, client id, scope, and output path all come
from the command line, so nothing environment specific lands in the repo. Run it with the
values for your org; keep the token file out of source control.

Examples:
    python signin.py \
        --authority https://login.microsoftonline.com/<tenant>/oauth2/v2.0 \
        --client-id <public-client-guid> \
        --scope "offline_access https://<org>.crm.dynamics.com/api/mcp_preview/mcp.tools" \
        --out ../build-notes/<org>-token.json

    python signin.py --refresh --out ../build-notes/<org>-token.json \
        --authority ... --client-id ... --scope ...
"""
import argparse
import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request
import webbrowser


def _b64url(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


class _CatchCode(http.server.BaseHTTPRequestHandler):
    code = None
    state = None
    error = None

    def do_GET(self):  # noqa: N802
        q = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(q)
        _CatchCode.code = (params.get("code") or [None])[0]
        _CatchCode.state = (params.get("state") or [None])[0]
        _CatchCode.error = (params.get("error_description") or params.get("error") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        msg = "Sign-in complete. You can close this tab and return to the terminal."
        if _CatchCode.error:
            msg = "Sign-in failed: %s" % _CatchCode.error
        self.wfile.write(("<html><body><h3>%s</h3></body></html>" % msg).encode())

    def log_message(self, *a):  # silence
        pass


def _post_token(token_url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(token_url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _save(out, tok):
    tok = dict(tok)
    if "expires_in" in tok:
        tok["expires_at"] = int(time.time()) + int(tok["expires_in"]) - 60
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(tok, f, indent=2)
    print("Saved token to %s (expires_at=%s)" % (out, tok.get("expires_at")))


def interactive(args):
    authorize_url = args.authority.rstrip("/") + "/authorize"
    token_url = args.authority.rstrip("/") + "/token"
    verifier = _b64url(secrets.token_bytes(64))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(16)
    redirect_uri = "http://localhost:%d/" % args.port

    server = http.server.HTTPServer(("127.0.0.1", args.port), _CatchCode)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    qs = urllib.parse.urlencode({
        "client_id": args.client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": args.scope,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    })
    url = authorize_url + "?" + qs
    print("Opening browser for sign-in. If it does not open, paste this URL:\n%s\n" % url)
    webbrowser.open(url)

    deadline = time.time() + args.timeout
    while _CatchCode.code is None and _CatchCode.error is None and time.time() < deadline:
        time.sleep(0.5)
    server.shutdown()

    if _CatchCode.error:
        raise SystemExit("Auth error: %s" % _CatchCode.error)
    if _CatchCode.code is None:
        raise SystemExit("Timed out waiting for sign-in.")
    if _CatchCode.state != state:
        raise SystemExit("State mismatch; aborting.")

    tok = _post_token(token_url, {
        "client_id": args.client_id,
        "grant_type": "authorization_code",
        "code": _CatchCode.code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
        "scope": args.scope,
    })
    _save(args.out, tok)


def refresh(args):
    with open(args.out, encoding="utf-8") as f:
        cur = json.load(f)
    rt = cur.get("refresh_token")
    if not rt:
        raise SystemExit("No refresh_token in %s; run interactive sign-in first." % args.out)
    token_url = args.authority.rstrip("/") + "/token"
    tok = _post_token(token_url, {
        "client_id": args.client_id,
        "grant_type": "refresh_token",
        "refresh_token": rt,
        "scope": args.scope,
    })
    if "refresh_token" not in tok:
        tok["refresh_token"] = rt
    _save(args.out, tok)


def main():
    p = argparse.ArgumentParser(description="Interactive MCP sign-in (auth-code + PKCE).")
    p.add_argument("--authority", required=True, help="OAuth v2.0 authority base (…/oauth2/v2.0)")
    p.add_argument("--client-id", required=True, help="public client app id")
    p.add_argument("--scope", required=True, help="space-separated scopes incl. offline_access")
    p.add_argument("--out", required=True, help="token output path (keep gitignored)")
    p.add_argument("--port", type=int, default=8765, help="loopback redirect port")
    p.add_argument("--timeout", type=int, default=300, help="seconds to wait for sign-in")
    p.add_argument("--refresh", action="store_true", help="refresh using the saved refresh_token")
    args = p.parse_args()
    if args.refresh:
        refresh(args)
    else:
        interactive(args)


if __name__ == "__main__":
    main()
