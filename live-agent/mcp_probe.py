"""Minimal Dataverse MCP client over streamable HTTP (standard library only).

Given a cached bearer token (see signin.py), this drives the MCP protocol directly:
initialize, then tools/list, then optional tools/call. It exists for Milestone 0 discovery,
enumerating which tools and tables an environment exposes, and how ERP data surfaces, without
depending on the Node SDK or the CLI extension host.

The endpoint may answer either application/json or text/event-stream (SSE); both are handled.
Nothing here hardcodes an environment: pass --url and --token-file.

Usage:
    python mcp_probe.py --url https://<org>.crm.dynamics.com/api/mcp_preview \
        --token-file ../build-notes/<org>-token.json --list
    python mcp_probe.py --url ... --token-file ... --call search --args "{\"...\":1}"
"""
import argparse
import json
import urllib.error
import urllib.request


def _load_token(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["access_token"]


def _parse_sse(body):
    """Return the last JSON object carried in an SSE 'data:' stream."""
    out = None
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                try:
                    out = json.loads(payload)
                except json.JSONDecodeError:
                    pass
    return out


class McpClient:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.session_id = None
        self._id = 0

    def _headers(self):
        h = {
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    def _post(self, method, params=None, notify=False):
        if notify:
            msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        else:
            self._id += 1
            msg = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        req = urllib.request.Request(self.url, data=json.dumps(msg).encode(), headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                sid = r.headers.get("Mcp-Session-Id")
                if sid:
                    self.session_id = sid
                ctype = r.headers.get("Content-Type", "")
                raw = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            raise RuntimeError("HTTP %s: %s" % (e.code, raw[:500]))
        if notify:
            return None
        if "text/event-stream" in ctype:
            return _parse_sse(raw)
        return json.loads(raw) if raw.strip() else None

    def initialize(self):
        resp = self._post("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "bskit-probe", "version": "1.0"},
        })
        self._post("notifications/initialized", notify=True)
        return resp

    def tools_list(self):
        return self._post("tools/list", {})

    def tools_call(self, name, arguments):
        return self._post("tools/call", {"name": name, "arguments": arguments})


def main():
    p = argparse.ArgumentParser(description="Probe a Dataverse MCP endpoint.")
    p.add_argument("--url", required=True)
    p.add_argument("--token-file", required=True)
    p.add_argument("--list", action="store_true", help="list tools")
    p.add_argument("--schema", help="print inputSchema for the named tool")
    p.add_argument("--call", help="tool name to call")
    p.add_argument("--args", default="{}", help="JSON arguments for --call")
    args = p.parse_args()

    client = McpClient(args.url, _load_token(args.token_file))
    init = client.initialize()
    info = (init or {}).get("result", {}).get("serverInfo", {})
    print("initialized: %s" % json.dumps(info))

    if args.list:
        res = client.tools_list()
        tools = (res or {}).get("result", {}).get("tools", [])
        print("tools (%d):" % len(tools))
        for t in tools:
            print("  - %s: %s" % (t.get("name"), (t.get("description") or "").split("\n")[0][:90]))

    if args.schema:
        res = client.tools_list()
        tools = (res or {}).get("result", {}).get("tools", [])
        for t in tools:
            if t.get("name") == args.schema:
                print(json.dumps(t.get("inputSchema", {}), indent=2)[:4000])
                break
        else:
            print("tool not found: %s" % args.schema)

    if args.call:
        res = client.tools_call(args.call, json.loads(args.args))
        print(json.dumps(res, indent=2)[:4000])


if __name__ == "__main__":
    main()
