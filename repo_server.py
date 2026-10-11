#!/usr/bin/env python3
"""pldmgr-selfhost: self-hosted private PS5 Payload Manager repository server.

Serves ./payloads/ over plain HTTP with a generated payloads.json in the
ps5-payload-manager "custom repository" format
(https://github.com/itsPLK/ps5-payload-manager/blob/main/CUSTOM_REPOSITORIES.md).

Features:
  - Drop any .elf/.bin/.lua into ./payloads/ (subfolders allowed) and it
    appears in the catalog instantly — SHA-256 checksums computed on the fly.
  - Optional GitHub release auto-mirroring: list repos in github_sources.json
    and their latest matching release assets are downloaded into
    payloads/github/<repo>/ (refreshed hourly, or POST /refresh).

Run: python3 repo_server.py [port]     (default 8090)

License: MIT
"""
import hashlib
import http.server
import json
import os
import re
import sys
import time
import urllib.request

__version__ = "0.1.0"

BASE = os.path.dirname(os.path.abspath(__file__))
PAYLOAD_DIR = os.environ.get("PAYLOAD_DIR", os.path.join(BASE, "payloads"))
GH_SRC = os.path.join(BASE, "github_sources.json")
REPO_NAME = os.environ.get("REPO_NAME", "My Private Payloads")
GH_TTL = int(os.environ.get("GH_REFRESH_SECONDS", "3600"))
_gh_last = 0.0
_EXT_RE = re.compile(r"\.(elf|bin|lua)$", re.I)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def guess_meta(filename):
    """Best-effort display name + version from a filename."""
    stem = os.path.splitext(filename)[0]
    m = re.search(r"v?(\d+[\w.\-]*\d)", stem)
    version = "v" + m.group(1) if m else ""
    name = re.sub(r"[_.]", " ", stem).strip()
    return name, version


def refresh_github(force=False):
    """Mirror latest release assets from github_sources.json into payloads/."""
    global _gh_last
    if not os.path.exists(GH_SRC):
        return
    if not force and (time.time() - _gh_last) < GH_TTL:
        return
    _gh_last = time.time()
    try:
        sources = json.load(open(GH_SRC))
    except Exception as e:
        print(f"[gh] bad github_sources.json: {e}", flush=True)
        return
    for src in sources:
        repo = src.get("repo", "")
        if not repo or "/" not in repo:
            continue
        include = re.compile(src.get("include", r"\.elf$"), re.I)
        tag = src.get("tag", "latest")
        suffix = "latest" if tag == "latest" else "tags/" + tag
        api = f"https://api.github.com/repos/{repo}/releases/{suffix}"
        req = urllib.request.Request(
            api, headers={"User-Agent": "pldmgr-selfhost",
                          "Accept": "application/vnd.github+json"})
        try:
            rel = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:
            print(f"[gh] {repo}: fetch failed: {e}", flush=True)
            continue
        dest = os.path.join(PAYLOAD_DIR, "github", repo.replace("/", "__"))
        os.makedirs(dest, exist_ok=True)
        for asset in rel.get("assets", []):
            if not include.search(asset["name"]):
                continue
            out = os.path.join(dest, asset["name"])
            if os.path.exists(out) and os.path.getsize(out) == asset["size"]:
                continue
            try:
                print(f"[gh] {repo}: downloading {asset['name']}", flush=True)
                urllib.request.urlretrieve(asset["browser_download_url"], out)
            except Exception as e:
                print(f"[gh] download {asset['name']} failed: {e}", flush=True)


def build_catalog():
    """Walk PAYLOAD_DIR and build the pldmgr-format catalog."""
    refresh_github()
    payloads = []
    for root, dirs, files in os.walk(PAYLOAD_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in sorted(files):
            if fn.startswith(".") or not _EXT_RE.search(fn):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, PAYLOAD_DIR)
            url = "/payloads/" + rel.replace(os.sep, "/")
            name, version = guess_meta(fn)
            category = "GitHub Mirror" if "github" in root.split(os.sep) else "My Collection"
            try:
                checksum = sha256(path)
            except OSError:
                continue  # file vanished mid-scan
            payloads.append({
                "name": name,
                "filename": fn,
                "url": url,
                "description": f"Self-hosted: {rel}",
                "version": version,
                "category": category,
                "checksum": checksum,
            })
    return {"name": REPO_NAME, "payloads": payloads}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=BASE, **kw)

    def end_headers(self):
        # CORS so the pldmgr web dashboard can fetch the catalog cross-origin.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/payloads.json":
            body = json.dumps(build_catalog(), indent=1).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Server-Version", __version__)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.split("?")[0] == "/version":
            body = f'{{"version": "{__version__}"}}\n'.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/refresh":
            refresh_github(force=True)
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        print("[http] " + fmt % args, flush=True)


def main():
    os.makedirs(PAYLOAD_DIR, exist_ok=True)
    if not os.path.exists(GH_SRC):
        with open(GH_SRC, "w") as f:
            json.dump([], f)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    print(f"pldmgr-selfhost v{__version__} serving on :{port}", flush=True)
    print(f"  catalog:    http://<host>:{port}/payloads.json", flush=True)
    print(f"  drop dir:   {PAYLOAD_DIR}", flush=True)
    http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()