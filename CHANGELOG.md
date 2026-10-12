# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.1] - 2026-10-12
### Changed
- Docker image now publishes as a multi-arch manifest (`linux/amd64` +
  `linux/arm64`) — the same image now runs natively on Raspberry Pi and
  other ARM64 boxes. (Thanks to the Reddit user who reported the Pi issue!)

## [0.1.0] - 2026-10-11

### Added
- Initial release: single-file Python HTTP server that serves a payload
  drop-folder as a `payloads.json` catalog in the ps5-payload-manager
  custom-repository format.
- Instant catalog rebuilds — files dropped into `payloads/` appear on the
  next request, no restart needed.
- Automatic SHA-256 checksums for every catalog entry.
- GitHub release auto-mirroring via `github_sources.json` (hourly refresh,
  `POST /refresh` to force).
- CORS headers (`Access-Control-Allow-Origin: *`) for the pldmgr web
  dashboard.
- `/version` endpoint and `X-Server-Version` header.
- Dockerfile and docker-compose.yml.

[Unreleased]: https://github.com/Bryanmoon19/pldmgr-selfhost/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Bryanmoon19/pldmgr-selfhost/releases/tag/v0.1.0