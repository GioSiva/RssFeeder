# AGENTS.md

Guidance for AI agents working in this repository.

## Project

**RssFeeder** — RSS feeds for custom webpages (see `README.md`). As of the initial commit, the repository contains documentation only; application source, tests, and service definitions are not present yet.

## Cursor Cloud specific instructions

### Repository state

- Single package at repo root (not a monorepo).
- No `package.json`, `pyproject.toml`, `docker-compose`, Makefile, or CI workflows until added by contributors.
- No lint, test, or build scripts are defined yet; skip those steps until they exist in the tree.

### VM toolchain (verified on Cloud Agent VMs)

- **Node.js** via nvm (`node`, `npm`) — use when JavaScript/TypeScript code is added.
- **Python 3.12** (`python3`, `pip`) — use when Python code is added.
- **Git** — standard clone/push workflow against `origin`.

Docker is not required for the current tree and may be unavailable on the VM unless installed for future containerized services.

### Running the application

There is no runnable service yet. After implementation:

1. Follow setup/run instructions in `README.md` or package-specific docs.
2. Rely on the VM **update script** (managed via SetupVmEnvironment) to refresh dependencies on session start — it only runs `npm install` when `package.json` exists and `pip install -r requirements.txt` when `requirements.txt` exists.

### Development workflow

- Create feature branches with the `cursor/<name>-8019` naming convention when working as a Cloud Agent.
- Do not assume ports, databases, or background workers until documented in the repo.
