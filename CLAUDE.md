# devenv-mcp
**License:** GNU GPLv3 -- all forks and derivatives must remain open source.

## What It Is
Unified MCP server: diagnostic layer for local dev environments.
Correlates process state, port conflicts, Docker health, and log errors
into structured root-cause reports. Accessible from any MCP-compatible
assistant (Claude, Cursor, etc.).

Core value: connecting signals, not just surfacing them.
"Port 5432 blocked by process X spawned by Docker container Y,
last 3 log lines: ..." is the output format to aim for.

## Stack
Python, mcp SDK, psutil, Docker SDK, JSON output.

## Formally Verifiable Scope (diagnoses these)
- Process state: running, zombie, blocked, resource usage
- Port conflicts + owning process identification
- Dependency version mismatches: Python, Node, system packages
- Docker container health, restart loops, resource exhaustion
- Structured log error extraction and pattern detection
- Environment variable presence/absence

## Out of Scope (never diagnoses these)
- Code logic errors
- Architectural decisions
- Anything requiring subjective judgment

This boundary is intentional. Every tool's docstring must reflect it.

## Guidance Policy (strict, never override)
Learning project. Never generate complete implementation code.
For any build question:
- Explain the mechanism and why it works
- Point to the right library, system call, or stdlib module
- Describe the data flow
- Outline the approach, leave implementation to the developer

If stuck: explain the concept, give targeted unblocking guidance only.
Goal is developer understands every line written.