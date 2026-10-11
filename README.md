# pldmgr-selfhost

**Self-hosted private payload repository for [PS5 Payload Manager](https://github.com/itsPLK/ps5-payload-manager).**

Run your own "cloud repository" source on your home network: drop payload files into a folder
(or let it auto-mirror GitHub releases), and they show up in Payload Manager's
cloud repo browser on your console — searchable, categorized, and SHA-256 verified.

This project ships **no payload binaries** and hosts none by default. It is a
content-agnostic file server + catalog generator; you point it at your own files.
Upstream payloads remain the property of their respective authors.

## The 3-step setup (if you have Docker)

1. **Start the server** — copy this into a terminal on any always-on computer
   (a Raspberry Pi, NAS, home server, whatever runs Docker):

   ```bash
   mkdir ps5-repo && cd ps5-repo
   curl -O https://raw.githubusercontent.com/<you>/pldmgr-selfhost/main/docker-compose.yml
   mkdir payloads
   docker compose up -d
   ```

2. **Put payloads in the folder** — drag `.elf` / `.bin` / `.lua` files into
   the `payloads` folder (FTP them over, browse to it over the network, whatever
   is easiest — subfolders are fine too).

3. **Add it on your PS5** — open **Payload Manager** → **Settings** →
   **Manage Sources** → **Add Source**, and paste:

   ```
   http://<the-computer's-ip>:8090/payloads.json
   ```

   Done. Your folder is now a catalog on your console, next to the official one.

> 💡 Find the computer's IP with `hostname -I` (Linux) or check your router's
> device list. The server prints its address on startup too.

## No Docker? 

```bash
python3 repo_server.py 8090
```

Requires Python 3.10+, no other dependencies (standard library only).

## Features

- 📂 **Drop folder** — any `.elf` / `.bin` / `.lua` placed in `payloads/`
  (subfolders allowed) appears in the catalog instantly. No restart, no rebuild.
- 🔐 **Automatic SHA-256 checksums** — every catalog entry is checksummed, so
  Payload Manager validates downloads on-console.
- 🐙 **GitHub auto-mirror** — list repos in `github_sources.json` and the latest
  matching release assets are downloaded automatically (hourly, or `POST /refresh`).
- 🌐 **CORS-ready, plain HTTP** — works around the on-console SSL verification
  quirks; ideal for home-network use.
- 🪶 **Zero dependencies** — single Python file, stdlib only.

## Keeping it updated

The Docker image is published to GitHub Container Registry on every release.
To update:

```bash
docker compose pull && docker compose up -d
```

Check what version you're running: `curl http://<ip>:8090/version`
(the catalog responses also carry an `X-Server-Version` header).

## Configuration

All optional — defaults work out of the box.

| Setting | Default | Purpose |
|---|---|---|
| `PAYLOAD_DIR` env | `./payloads` | Folder scanned for payload files (point at a NAS share) |
| `REPO_NAME` env | `My Private Payloads` | Catalog name shown in Payload Manager |
| `GH_REFRESH_SECONDS` env | `3600` | How often to check GitHub for new releases |
| `github_sources.json` | empty | List of GitHub repos to auto-mirror |

### GitHub auto-mirror (`github_sources.json`)

Want new payloads to appear automatically when their developers publish a
release? List the GitHub repos:

```json
[
  {
    "repo": "ps5-payload-dev/ftpsrv",
    "include": "\\.elf$",
    "tag": "latest"
  }
]
```

- `include` — a pattern matched against release asset names (default `\.elf$`)
- `tag` — `latest` (default) or a specific release tag

Mirrored files land in `payloads/github/<owner>__<repo>/` under the
**GitHub Mirror** category. To check for updates right away:

```bash
curl -X POST http://<ip>:8090/refresh
```

## Security notes

- **Keep it on your home network.** Do NOT port-forward this to the internet —
  anyone who can reach the catalog can make your console run those payloads.
- The server is **unauthenticated** by design (Payload Manager sends no
  credentials) — that's fine on a trusted LAN, unsafe on the public internet.
- If you ever must expose it beyond home, put it behind a reverse proxy with
  authentication and only open the JSON + download routes.

## Found a problem or have an idea?

Open an issue — the templates ask a few quick questions (your version, what
happened, what you expected). For the version, `curl http://<ip>:8090/version`
gives you the answer to paste in.

## Catalog format

The generated `payloads.json` follows Payload Manager's
[CUSTOM_REPOSITORIES.md](https://github.com/itsPLK/ps5-payload-manager/blob/main/CUSTOM_REPOSITORIES.md)
spec (top-level `name` before `payloads`, SHA-256 `checksum` per item).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) — versions follow [Semantic Versioning](https://semver.org/).

## License

MIT — see [LICENSE](LICENSE). This project is not affiliated with itsPLK or
the Payload Manager project; it simply implements their public custom-source spec.

## Credits

- [itsPLK/ps5-payload-manager](https://github.com/itsPLK/ps5-payload-manager) — the manager and its custom repository spec
- [lucaszhongsj/ps5-payloads-atlas](https://github.com/lucaszhongsj/ps5-payloads-atlas) — the public-catalog cousin of this private-server idea