import json, os, sys, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

UPSTREAM = os.environ.get("UPSTREAM_SOURCE_URL", "https://repository.apptesters.org/")
OUT = Path(os.environ.get("OUTPUT_DIR", "site"))

def fetch():
    req = urllib.request.Request(UPSTREAM, headers={
        "User-Agent": "PAL-Source-Validator/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        if r.status != 200:
            raise RuntimeError(f"Upstream HTTP {r.status}")
        data = json.loads(r.read().decode("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("apps"), list):
        raise ValueError("Expected a JSON object with an apps array")
    return data

def valid_http(url):
    try:
        p = urlparse(url)
        return p.scheme in ("https", "http") and bool(p.netloc)
    except Exception:
        return False

def is_adp_manifest(url):
    if not isinstance(url, str) or not valid_http(url):
        return False
    return urlparse(url).path.lower().rstrip("/").endswith("/manifest.json") or urlparse(url).path.lower() == "/manifest.json"

def validate(app):
    issues = []
    if not isinstance(app, dict):
        return False, ["entry is not an object"]
    for key in ("name", "bundleIdentifier", "developerName", "marketplaceID"):
        if not isinstance(app.get(key), str) or not app[key].strip():
            issues.append(f"missing {key}")
    versions = app.get("versions")
    if not isinstance(versions, list) or not versions:
        issues.append("missing versions")
        return False, issues
    good = []
    for i, v in enumerate(versions):
        if not isinstance(v, dict):
            issues.append(f"version {i} is not an object")
            continue
        missing = [k for k in ("version", "buildVersion", "date", "downloadURL") if str(v.get(k, "")).strip() == ""]
        if missing:
            issues.append(f"version {i} missing {', '.join(missing)}")
        elif is_adp_manifest(v["downloadURL"]):
            good.append(v)
        else:
            issues.append(f"version {i} URL is not an explicit ADP manifest.json URL")
    if not good:
        issues.append("no PAL-shaped ADP versions")
    return not issues, issues

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        upstream = fetch()
    except Exception as e:
        print(f"Fetch/parse failed: {e}", file=sys.stderr)
        sys.exit(1)

    accepted, rejected = [], []
    for app in upstream["apps"]:
        ok, reasons = validate(app)
        name = app.get("name", "(unnamed)") if isinstance(app, dict) else "(invalid entry)"
        if ok:
            accepted.append(app)
        else:
            rejected.append({"name": name, "reasons": reasons})

    result = {k: v for k, v in upstream.items() if k != "apps"}
    result.setdefault("name", "AppTesters PAL-filtered source")
    result.setdefault("subtitle", "Conservative PAL metadata filter")
    result.setdefault("description", "Filtered metadata from AppTesters. Passing checks does not prove notarization.")
    result.setdefault("news", [])
    result["apps"] = accepted
    (OUT / "source.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "upstream": UPSTREAM,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "upstreamAppCount": len(upstream["apps"]),
        "includedAppCount": len(accepted),
        "excludedAppCount": len(rejected),
        "includedNames": [a.get("name", "") for a in accepted],
        "excluded": rejected,
        "note": "Metadata and URL-shape checks only. Notarization and ADP signatures are not independently verified."
    }
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "index.html").write_text(HTML, encoding="utf-8")
    print(f"Apps upstream={len(upstream['apps'])}, included={len(accepted)}, excluded={len(rejected)}")

HTML = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AppTesters PAL Filter</title>
<style>
body{margin:0;background:#0c1017;color:#eef3fb;font:16px/1.55 system-ui,sans-serif}main{max-width:760px;margin:auto;padding:32px 18px}
.card{background:#151c27;border:1px solid #2a3546;border-radius:16px;padding:20px;margin:16px 0}
h1{font-size:clamp(2rem,6vw,3rem);line-height:1.1}p{color:#b4bfd0}a,button{display:inline-block;background:#b6d0ff;color:#101722;border:0;border-radius:10px;padding:11px 14px;font-weight:700;text-decoration:none;cursor:pointer;margin:5px 5px 5px 0}
code{overflow-wrap:anywhere;color:#b6d0ff}.warning{border-left:3px solid #e7b96c;padding:10px 14px;background:#251f16;color:#e9d9bd}
</style><main><p>GITHUB PAGES · GENERATED SOURCE</p><h1>AppTesters PAL filter</h1>
<p>Only entries passing conservative metadata and URL-shape checks are included. This tool does not create marketplace IDs or notarize apps.</p>
<div class="card"><p id="stats">Loading report…</p><p>Source URL: <code id="url"></code></p><a id="open" href="./source.json">Open source JSON</a><button id="copy">Copy source URL</button><a href="./report.json">Validation report</a></div>
<div class="warning">Passing the filter does not prove Apple notarization or ADP signature validity. If zero apps pass, the upstream library cannot be converted into a PAL source by editing JSON.</div>
<p>Upstream: <a href="https://repository.apptesters.org/">AppTesters repository</a>. Independent project, not affiliated with AppTesters or AltStore.</p>
<script>
const u=new URL("source.json",location.href).href;document.getElementById("url").textContent=u;document.getElementById("open").href=u;
fetch("report.json").then(r=>r.json()).then(d=>document.getElementById("stats").textContent=`Upstream: ${d.upstreamAppCount} · Included: ${d.includedAppCount} · Excluded: ${d.excludedAppCount} · Generated: ${new Date(d.generatedAt).toLocaleString()}`).catch(()=>document.getElementById("stats").textContent="Report unavailable.");
document.getElementById("copy").onclick=async()=>{try{await navigator.clipboard.writeText(u);document.getElementById("copy").textContent="Copied"}catch{prompt("Copy source URL",u)}};
</script></main></html>
"""

if __name__ == "__main__":
    main()
