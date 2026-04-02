# Roadmap Guide

English | [简体中文](../zh-CN/roadmap.md)

The runtime MVP is complete.
Track A, Track B, and Track C first slices are now in place.
Near-term work is now focused on companion executable packaging over the beta-hardened outsider path rather than widening the canonical runtime surface.

## Current priority order

1. keep companion executable packaging coherent across bundled demo assets, `mcp --demo`, and companion build/smoke paths
2. execute the current-requirement bootstrap path over the thin workspace substrate
3. extend the local governed companion flow with workspace-backed guided validation while the public MCP surface stays read-only
4. widen non-developer distribution only after the companion path and bootstrap path stay coherent under repeated verification
5. add adapters only after the companion outsider path stays coherent under repeated verification
