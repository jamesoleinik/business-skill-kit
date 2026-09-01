"""Minimal Dataverse Web API action client (standard library only).

The MCP surface exposes record CRUD but not the managed *messages* that drive record state
transitions -- winning an opportunity or resolving a case. MCP rejects a direct statecode
write ("use the won message instead" / "use the CloseIncidentRequest message instead").
Those messages are ordinary Web API actions on the very same org host the MCP endpoint lives
on, so this helper posts them directly, authenticated with a token minted for the org's Web
API scope (`.../.default`, which yields `user_impersonation`).

Nothing environment-specific is hardcoded: pass the org base URL and a token file. Keep the
token gitignored (build-notes/), exactly like the MCP token.
"""
import json
import urllib.error
import urllib.parse
import urllib.request


def load_token(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["access_token"]


def org_base(url):
    """Reduce any org URL (e.g. the MCP endpoint) to scheme://host."""
    p = urllib.parse.urlparse(url)
    return "%s://%s" % (p.scheme, p.netloc)


class WebApiClient:
    def __init__(self, base_url, token, version="v9.2"):
        self.base = "%s/api/data/%s/" % (org_base(base_url).rstrip("/"), version)
        self.token = token

    def _headers(self):
        return {"Authorization": "Bearer " + self.token,
                "Content-Type": "application/json", "Accept": "application/json"}

    def action(self, name, payload):
        req = urllib.request.Request(
            self.base + name, data=json.dumps(payload).encode(), headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode()
                return r.status, (json.loads(body) if body.strip() else None)
        except urllib.error.HTTPError as e:
            raise RuntimeError("Web API %s -> HTTP %s: %s"
                               % (name, e.code, e.read().decode()[:400]))

    def win_opportunity(self, opportunity_id, status=3, subject="Won"):
        return self.action("WinOpportunity", {
            "Status": status,
            "OpportunityClose": {
                "subject": subject,
                "opportunityid@odata.bind": "/opportunities(%s)" % opportunity_id,
            }})

    def close_incident(self, incident_id, status=5, subject="Resolved"):
        return self.action("CloseIncident", {
            "Status": status,
            "IncidentResolution": {
                "subject": subject,
                "incidentid@odata.bind": "/incidents(%s)" % incident_id,
            }})
