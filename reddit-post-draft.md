# Reddit launch post — pldmgr-selfhost

**Target sub:** r/ps5homebrew (primary), optional crosspost r/PlaystationScene
**Flair:** Tool / Release / Homebrew (pick "Tool" if available)
**Title (<=300 chars, no clickbait):**

I made a self-hosted "cloud repository" server for Payload Manager — your own private source, drop-folder + auto GitHub mirroring (free, open source)

**Body:**

---

If you use **Payload Manager** (itsPLK), you've probably seen the "Cloud Repository" section and the official mirror. I kept wishing I could point it at *my own* collection — private payloads, stuff that's not on any public repo, things I want to keep for myself across reinstalls.

So I built **pldmgr-selfhost**: a tiny server that runs on your LAN and serves a folder as a custom pldmgr source.

## What it does

- 📂 **Drop folder**: any `.elf` / `.bin` / `.lua` you put in `payloads/` shows up on your console instantly — subfolders become categories/organization
- 🔐 **Automatic SHA-256 checksums** for every file, so the console verifies downloads
- 🐙 **GitHub auto-mirror**: list repos + release asset patterns in `github_sources.json` and it pulls new payloads from GitHub releases automatically (hourly, or on-demand via `POST /refresh`)
- 🐳 **Docker image published** (`ghcr.io/bryanmoon19/pldmgr-selfhost:latest`) or run it with bare Python — it's a single file, **zero dependencies**, stdlib only (Python 3.10+)
- 🛡️ Hardened: file serving is restricted to the payloads directory (path-traversal and symlink attempts blocked — I adversarially tested it before release)

## What it doesn't do

- **It doesn't jailbreak the console** — you need a working jailbreak (and Payload Manager installed) first.
- **It doesn't ship payloads** — no binaries, nothing preloaded. It's just the server; your collection stays yours.
- **It's not a public mirror** — if you want the community repos, use the official sources. This is for *your* files.

## Setup is 3 steps

1. Start the container (one copy-paste block in the README)
2. Drop payload files in the folder
3. In Payload Manager → Cloud Repository → add `http://<your-pc-ip>:8090/payloads.json`

The catalog rebuilds on every request, so there's no refresh/cache to think about — new files just appear. Plain HTTP on purpose, because of the SSL quirks we all know about.

## Important

- **Keep it on your LAN** — don't port-forward it. It's unauthenticated by design (home network only).
- Ships **no payload binaries** — it's just the server. What you host is your business.
- **Not affiliated with itsPLK** — I just implemented their public custom-repository spec. Big thanks to them for documenting it.
- **Yes, I built this with AI assistance** — and I'd rather say it upfront than have someone dig through the commits. That said, I don't think it's a case of "vibe-coded and yeeted": the whole server is one ~200-line stdlib-only Python file you can read in five minutes, it was adversarially security-tested before release (path traversal, encoding tricks, symlinks — all blocked), and it's MIT licensed so you can verify every line yourself. AI wrote the code; I did the testing, threat modeling, and I'm running it on my own network daily. Judge the tool, not how it was written 🙂

🔗 **GitHub:** https://github.com/Bryanmoon19/pldmgr-selfhost
🐳 **Docker:** `ghcr.io/bryanmoon19/pldmgr-selfhost:latest`
📜 MIT licensed. Feedback and feature requests very welcome (issue templates are set up) — I'm dogfooding it daily on my own setup. Free forever, no premium tier, no telemetry. If you want to support continued development, starring the repo and sharing feedback is honestly the best donation there is.

Happy to answer questions in the comments — I'll be hanging around the thread.

---

## Post notes (for us, don't publish)
- Post from Bryan's account, NOT from any bot.
- Best posting window: weekday evening or weekend morning (scene traffic).
- rdt-cli is broken in headless sessions — post manually via browser, or use the browser tool when ready.
- Do NOT mention it's "for private/pirated payloads" framing — keep it "private collection, your own files" (same framing as above).
- **Poster image ready: `assets/reddit-poster.png`** (1800×882 dark-theme flow diagram) — attach as the post image for the feed preview card.
- Post format on Reddit: use the **Fancy Pants editor** (or markdown) — the body above is ready to paste as-is; the `##` headers become bold headers on new Reddit.
- After posting: check `new` tab of r/ps5homebrew to confirm it's not caught in the spam filter (new accounts' tool posts occasionally need mod approval). Message mods via modmail if stuck >30 min.
- Crosspost later, not at launch — let r/ps5homebrew build initial comments first (crossposts to r/PlaystationScene can follow in 24-48h if traction is good).