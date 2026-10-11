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
import urllib.parse
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
            checksum = _checksum_cached(path)
            if checksum is None:
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


# mtime+size keyed checksum cache so big files aren't re-hashed on every request
_ck_cache = {}


def _checksum_cached(path):
    try:
        st = os.stat(path)
        key = (path, st.st_mtime_ns, st.st_size)
        hit = _ck_cache.get(path)
        if hit and hit[0] == key:
            return hit[1]
        value = (sha256(path), key)
        _ck_cache[path] = value
        return value[0]
    except OSError:
        return None


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    def end_headers(self):
        # CORS so the pldmgr web dashboard can fetch the catalog cross-origin.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _serve_payload_file(self, rel_url_path):
        """Serve a file from PAYLOAD_DIR only. Rejects anything that resolves
        outside it (path traversal, symlinks)."""
        rel = urllib.parse.unquote(rel_url_path)
        # normalize and verify the resolved path stays inside PAYLOAD_DIR
        target = os.path.realpath(os.path.join(PAYLOAD_DIR, rel))
        root = os.path.realpath(PAYLOAD_DIR)
        if target != root and not target.startswith(root + os.sep):
            self.send_error(403)
            return
        if not os.path.isfile(target):
            self.send_error(404)
            return
        ctype = self.guess_type(target)
        try:
            with open(target, "rb") as f:
                fs = os.fstat(f.fileno())
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified",
                         self.date_time_string(fs.st_mtime))
        self.end_headers()
        try:
            self.copyfile(open(target, "rb"), self.wfile)
        except OSError:
            pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/payloads.json":
            body = json.dumps(build_catalog(), indent=1).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Server-Version", __version__)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/version":
            body = f'{{"version": "{__version__}"}}\n'.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path.startswith("/payloads/"):
            self._serve_payload_file(path[len("/payloads/"):])
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/refresh":
            refresh_github(force=True)
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        print("[http] " + fmt % args, flush=True)


def _lan_ips():
    """Return the machine's LAN IPv4 addresses (best effort, no external calls)."""
    ips = []
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("10.255.255.255", 1))  # never sent; just picks a route
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        import socket
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips


def main():
    os.makedirs(PAYLOAD_DIR, exist_ok=True)
    if not os.path.exists(GH_SRC):
        with open(GH_SRC, "w") as f:
            json.dump([], f)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    print(f"pldmgr-selfhost v{__version__} serving on :{port}", flush=True)
    print(f"  drop dir:   {PAYLOAD_DIR}", flush=True)
    # Print every LAN IP with the full URL to paste into Payload Manager,
    # so users don't have to hunt for the server's address.
    print(f"  Add this URL in Payload Manager (pick your network's):", flush=True)
    ips = _lan_ips()
    if ips:
        for ip in ips:
            print(f"    http://{ip}:{port}/payloads.json", flush=True)
    else:
        print(f"    http://<this-computer's-ip>:{port}/payloads.json", flush=True)
    http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()