"""Optional live mode: a strictly read-only Dataverse Web API client.

The kit runs on the synthetic fixture by default. This adapter lets the same read patterns
run against a real Dataverse environment for a connectivity and read smoke test. It is
read-only by construction: it exposes GET-based helpers only and never writes. A bearer
token is obtained from the Azure CLI (`az account get-access-token`) for the target org
resource, so no secret is stored in code or committed.

Usage is opt-in and separate from the fixture-based skills; see scripts/live_smoke.py.
"""
import json
import subprocess
import urllib.parse
import urllib.request


class LiveError(Exception):
    pass


def get_token(resource):
    """Get a bearer token for the Dataverse resource via the Azure CLI. Read-only use."""
    try:
        p = subprocess.run(
            'az account get-access-token --resource "%s" --query accessToken -o tsv' % resource,
            shell=True, capture_output=True, text=True,
        )
    except Exception as e:  # noqa: BLE001
        raise LiveError("could not run az: %s" % e)
    token = (p.stdout or "").strip()
    if p.returncode != 0 or not token:
        raise LiveError("az did not return a token: %s" % (p.stderr or "").strip())
    return token


class LiveStore:
    """Read-only view over a Dataverse environment. GET only; no create/update/delete."""

    def __init__(self, url, token=None, api_version="v9.2"):
        self.url = url.rstrip("/")
        self.api = "%s/api/data/%s/" % (self.url, api_version)
        self._token = token or get_token(self.url)

    def _get(self, path):
        req = urllib.request.Request(
            self.api + path,
            headers={
                "Authorization": "Bearer %s" % self._token,
                "OData-Version": "4.0",
                "Accept": "application/json",
                "Prefer": 'odata.maxpagesize=50',
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:  # noqa: PERF203
            raise LiveError("HTTP %s on %s: %s" % (e.code, path, e.read().decode("utf-8", "ignore")[:300]))

    def whoami(self):
        return self._get("WhoAmI")

    def query(self, entityset, select=None, top=None, filter=None, order_by=None):
        params = {}
        if select:
            params["$select"] = ",".join(select)
        if top:
            params["$top"] = str(top)
        if filter:
            params["$filter"] = filter
        if order_by:
            params["$orderby"] = order_by
        qs = urllib.parse.urlencode(params, safe="=,$ ()'")
        path = entityset + (("?" + qs) if qs else "")
        return self._get(path).get("value", [])

    def count(self, entityset, filter=None):
        return len(self.query(entityset, select=[entityset[:-1] + "id"], top=5000, filter=filter))
