# ☽ Saint Charon — Drive Recovery Engine Music Generator

**"Ferryman of Lost Data"** — a real-time 3D dashboard, API server, and vaporwave music engine for monitoring and controlling disk recovery operations.

![Saint Charon](saint_charon.html)

## Overview

Saint Charon is a comprehensive drive recovery orchestration system that combines:

- **🩺 Block Recovery** — ddrescue imaging with live sector-level 3D visualization
- **⚠️ Bad Sector Mapping** — 3D defrag-style map of damaged regions
- **🔬 File Carving** — foremost extraction with real-time file type tracking
- **🏷 EXIF Classification** — automated sorting of recovered photos/videos from memes
- **📡 Data Migration** — rsync pipeline to Immich & Jellyfin libraries
- **✅ Verification** — checksum cross-checking

Every stage has a **Three.js 3D scene** and a **Web Audio API vaporwave sonifier** that turns recovery metrics into generative music.

## Quick Start

```bash
# Install dependencies
pip install numpy python-osc mido

# Start the dashboard server
python3 server.py
# → http://localhost:8765/saint_charon.html

# (Optional) Run the live status refresher
python3 refresh_charts.py

# (Optional) Run the generative music engine
python3 sonify.py --verbose --interval 3

# (Optional) Render a vaporwave track from recovery data
python3 vaporwave_synth.py --status /tmp/status.json --out recovery_beats.wav
```

## Configuration

| Env Var | Default | Description |
|----------|---------|-------------|
| `SSH_HOST` | `zima` | SSH hostname for the recovery server |
| `HTML_DIR` | `~/Projects/narwal` | Directory containing dashboard HTML files |
| `PORT` | `8765` | HTTP server port |

The recovery server needs these scripts at `/srv/photos/`:
- `zima_status.sh` — reports ddrescue + migration status
- `foremost_status.sh` — reports file carving progress
- `classify_media.sh` — EXIF-based photo/video classifier
- `classify_status.sh` — reports classification progress

## Architecture

```
┌─────────────────────────────────────────────────┐
│  saint_charon.html (Three.js + Web Audio)       │
│  Dashboard with 8 stages, 3D scenes, sonifiers  │
├─────────────────────────────────────────────────┤
│  server.py (HTTP API)                           │
│  /status.json  /api/start-classify  ...         │
├─────────────────────────────────────────────────┤
│  refresh_charts.py (Data pipeline)              │
│  Pulls status via SSH → writes status.json      │
├─────────────────────────────────────────────────┤
│  sonify.py (MIDI/OSC bridge)                    │
│  vaporwave_synth.py (Audio renderer)            │
│  Data-driven generative music engine            │
└─────────────────────────────────────────────────┘
         │ SSH
         ▼
┌─────────────────────────────────────────────────┐
│  Recovery Server (Linux)                        │
│  ddrescue → foremost → classify → rsync         │
└─────────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `saint_charon.html` | Main dashboard (Three.js 3D + Web Audio sonifiers) |
| `server.py` | HTTP API server with action endpoints |
| `refresh_charts.py` | Status data pipeline (SSH → JSON → HTML embed) |
| `sonify.py` | Vaporwave sonification engine (MIDI + OSC output) |
| `vaporwave_synth.py` | Offline audio renderer (WAV output) |
| `la_migra.html` | Migration tracking dashboard |
| `orpheus.html` | File recovery tracking dashboard |

## License

MIT
