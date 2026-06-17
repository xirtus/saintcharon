#!/usr/bin/env python3
"""Pull live status from recovery server, write status.json + update HTML embedded fallback data.

Configuration:
  SSH_HOST — env var for the recovery server SSH host (default: zima)
"""
import subprocess, re, sys, os, json, tempfile
from datetime import datetime, timezone

SSH_HOST = os.environ.get("SSH_HOST", "zima")

HTML_PATH = os.path.expanduser("~/Projects/narwal/immich_jellyfin_migration_plan.html")
LA_MIGRA_PATH = os.path.expanduser("~/Projects/narwal/la_migra.html")
JSON_PATH = "/tmp/status.json"
FOREMOST_CACHE = "/tmp/foremost_cache.json"

def ssh_zima(script_name="zima_status.sh"):
    result = subprocess.run(
        ["ssh", SSH_HOST, f"bash /srv/photos/{script_name}"],
        capture_output=True, text=True, timeout=30
    )
    data = {}
    for line in result.stdout.strip().split("\n"):
        if "=" in line:
            k, v = line.split("=", 1)
            data[k] = v
    return data

def build_foremost_json(data):
    return {
        "running": data.get("foremost_running", "0") == "1",
        "pid": data.get("foremost_pid", "0"),
        "pct": float(data.get("foremost_pct", 0)),
        "cpu": data.get("foremost_cpu", "0"),
        "elapsed_s": int(data.get("foremost_elapsed", 0)),
        "eta_h": int(data.get("foremost_eta_h", 0)),
        "eta_m": int(data.get("foremost_eta_m", 0)),
        "total_files": int(data.get("foremost_total", 0)),
        "total_size": data.get("foremost_size", "0"),
        "by_type": {
            "jpg": int(data.get("foremost_jpg", 0)),
            "png": int(data.get("foremost_png", 0)),
            "mp4": int(data.get("foremost_mp4", 0)),
            "mov": int(data.get("foremost_mov", 0)),
            "gif": int(data.get("foremost_gif", 0)),
            "avi": int(data.get("foremost_avi", 0)),
            "wav": int(data.get("foremost_wav", 0)),
            "pdf": int(data.get("foremost_pdf", 0)),
            "zip": int(data.get("foremost_zip", 0)),
            "htm": int(data.get("foremost_htm", 0)),
            "other": int(data.get("foremost_other", 0)),
        },
        "last_log": data.get("foremost_lastlog", ""),
        "generated_at": data.get("generated_at", ""),
    }

def build_status_json(data):
    dd_run = data.get("dd_running", "0") == "1"
    folders_out = {}
    folder_defs = [
        ("7gopro",  61,   50),
        ("Quik",    2,    0.162),
        ("Contest", 3,    2.3),
        ("360gopro",209,  339),
        ("BRITNEEE",177,  8.9),
        ("eurotrip",8075, 705),
    ]
    for name, total_files, total_gb in folder_defs:
        folders_out[name] = {
            "files_done": int(data.get(f"{name}_files", 0)),
            "files_total": total_files,
            "gb_done": float(data.get(f"{name}_size", 0)),
            "gb_total": total_gb,
        }
    return {
        "generated_at": data.get("generated_at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
        "ddrescue": {
            "running": dd_run,
            "pct": float(data.get("pct", 0)),
            "rescued_gb": data.get("rescued_gb", "?"),
            "total_gb": data.get("total_gb", "?"),
            "bad_sectors": data.get("bad_sectors", "0"),
            "bad_kb": data.get("bad_kb", "?"),
            "rate_gb_h": data.get("rate_gb_h", "?"),
            "eta_h": data.get("eta_h", "?"),
        },
        "folders": folders_out,
        "auto_running": data.get("auto_running", "0") == "1",
        "auto_pid": data.get("auto_pid", "?"),
    }

def update_html_embedded(status):
    """Update the window.__INITIAL_STATUS__ in the HTML so file:// users see fresh data."""
    try:
        with open(HTML_PATH, "r") as f:
            html = f.read()
    except FileNotFoundError:
        print(f"  HTML not found at {HTML_PATH}, skipping embedded update", file=sys.stderr)
        return

    dd = status["ddrescue"]
    fm = status.get("foremost")
    pct = dd["pct"]
    ts = status["generated_at"]

    # 1. Update the embedded JSON blob
    new_blob = f"window.__INITIAL_STATUS__ = {json.dumps(status)};"
    html = re.sub(
        r'window\.__INITIAL_STATUS__\s*=\s*\{[\s\S]*?\};',
        new_blob, html, flags=re.DOTALL)

    # 2. Update Stage 0 card fallback values
    html = re.sub(
        r'(<span class="value" id="dd-card-progress-text">)[^<]*(</span>)',
        rf'\g<1>~{pct:.1f}% — ~{dd["rescued_gb"]} GB rescued of {dd["total_gb"]} GB (as of {ts})\g<2>',
        html)
    circ = 2 * 3.1415926535 * 42
    offset = circ - ((pct / 100) * circ)
    html = re.sub(
        r'(stroke-dashoffset=")[\d.]+(")',
        rf'\g<1>{offset:.2f}\g<2>', html)
    html = re.sub(
        r'(<span class="ring-pct" id="dd-ring-pct"[^>]*>)[\d.]+%(</span>)',
        rf'\g<1>{pct:.1f}%\g<2>', html)
    html = re.sub(
        r'(<div class="progress-bar-fill" id="dd-card-progress" style="width:)[\d.]+%',
        rf'\g<1>{pct:.1f}%', html)
    html = re.sub(
        r'(<span class="value" style="color:var\(--red\)" id="dd-card-errors">)[^<]*(</span>)',
        rf'\g<1>{dd["bad_sectors"]} <span style="font-size:0.75rem;color:var(--overlay0)">({dd["bad_kb"]} KB)</span>\g<2>',
        html)
    eta_text = f'~{dd["eta_h"]} hours (live-updating)' if dd["running"] else "Complete"
    html = re.sub(
        r'(<span class="value" id="dd-card-eta">)[^<]*(</span>)',
        rf'\g<1>{eta_text}\g<2>', html)
    header_html = f'🩺 ddrescue live — <strong>{pct:.1f}%</strong> complete ({dd["rescued_gb"]} / {dd["total_gb"]} GB) — updated {ts}'
    html = re.sub(
        r'(id="header-date">)[^<]*(</span>)',
        rf'\g<1>{header_html}\g<2>', html)

    # 3. Update foremost fallback values if available
    if fm:
        fm_pct = fm.get("pct", 0)
        fm_total = fm.get("total_files", 0)
        fm_size = fm.get("total_size", "0")
        # Progress bar width
        html = re.sub(
            r'(<div class="progress-bar-fill" id="foremost-progress-bar" style="width:)[\d.]+%(;background:linear-gradient\(90deg,var\(--accent\),var\(--mauve\)\)">)',
            rf'\g<1>{max(fm_pct, 0.5):.1f}%\g<2>', html)
        # Progress label
        html = re.sub(
            r'(id="foremost-progress-label">)[\d.]+%( scanned</span>)',
            rf'\g<1>{fm_pct:.1f}\g<2>', html)
        # Total files label
        html = re.sub(
            r'(id="foremost-total-label">)[\d,]+( files recovered</strong>)',
            rf'\g<1>{fm_total:,}\g<2>', html)
        # Total size label
        html = re.sub(
            r'(id="foremost-size-label">)[^<]*(</span>)',
            rf'\g<1>{fm_size}\g<2>', html)
        # File type counters
        by_type = fm.get("by_type", {})
        for ftype, el_id in [("jpg","fc-jpg"),("png","fc-png"),("mp4","fc-mp4"),("mov","fc-mov"),
                              ("gif","fc-gif"),("wav","fc-wav"),("pdf","fc-pdf"),("zip","fc-zip"),("other","fc-other")]:
            val = by_type.get(ftype, 0)
            html = re.sub(
                rf'(id="{el_id}">)[\d,]+(</div>)',
                rf'\g<1>{val:,}\g<2>', html)
        # Status dot and text
        if fm.get("running"):
            html = re.sub(
                r'(id="foremost-dot")[^>]*>',
                r'\g<1> class="scan-dot active">', html)
            html = re.sub(
                r'(id="foremost-status-text">)[^<]*(</span>)',
                rf'\g<1>Scanning image at {fm_pct:.1f}%\g<2>', html)

    with open(HTML_PATH, "w") as f:
        f.write(html)

def update_la_migra_embedded(status):
    """Update the window.__INITIAL_STATUS__ in la_migra.html for instant load."""
    try:
        with open(LA_MIGRA_PATH, "r") as f:
            html = f.read()
    except FileNotFoundError:
        return

    new_blob = f"window.__INITIAL_STATUS__ = {json.dumps(status)};"
    html = re.sub(
        r'window\.__INITIAL_STATUS__\s*=\s*\{[\s\S]*?\};',
        new_blob, html, flags=re.DOTALL)

    with open(LA_MIGRA_PATH, "w") as f:
        f.write(html)


def main():
    try:
        data = ssh_zima()
    except Exception as e:
        print(f"ERROR fetching status: {e}", file=sys.stderr)
        sys.exit(1)

    if not data:
        print("No data from Zima", file=sys.stderr)
        sys.exit(1)

    status = build_status_json(data)

    # Also fetch foremost status (with timeout handling and caching)
    fdata = None
    try:
        fdata = ssh_zima("foremost_status.sh")
    except Exception as e:
        print(f"  (foremost status fetch failed: {e})", file=sys.stderr)

    if fdata:
        foremost = build_foremost_json(fdata)
        status["foremost"] = foremost
        # Cache successful foremost data
        try:
            with open(FOREMOST_CACHE, "w") as fc:
                json.dump(foremost, fc)
        except Exception:
            pass
    else:
        # Try to use cached foremost data
        try:
            with open(FOREMOST_CACHE, "r") as fc:
                cached = json.load(fc)
                cached["running"] = True  # assume still running since we can't check
                status["foremost"] = cached
                status["foremost"]["_cached"] = True
                print(f"  (using cached foremost data: {cached.get('total_files',0)} files, {cached.get('pct',0):.1f}%)", file=sys.stderr)
        except Exception:
            status["foremost"] = None
            print(f"  (no foremost data available — no cache either)", file=sys.stderr)

    # Write atomically to avoid readers seeing partial files
    tmpfd, tmppath = tempfile.mkstemp(dir="/tmp", prefix="status_", suffix=".json")
    try:
        with os.fdopen(tmpfd, "w") as f:
            json.dump(status, f)
        os.replace(tmppath, JSON_PATH)  # atomic on Linux
    except Exception:
        # Fallback to direct write
        with open(JSON_PATH, "w") as f:
            json.dump(status, f)
        if os.path.exists(tmppath):
            os.unlink(tmppath)

    # Update HTML embedded data
    update_html_embedded(status)
    update_la_migra_embedded(status)

    dd = status["ddrescue"]
    auto = ""
    if status["auto_running"]:
        auto = f" | Auto-migration running (PID {status['auto_pid']})"
    fm = status.get("foremost")
    fm_str = ""
    if fm and fm["running"]:
        fm_str = f" | Foremost: {fm['total_files']} files ({fm['pct']:.1f}%)"
    print(f"✅ {status['generated_at']} — ddrescue: {dd['pct']:.1f}% ({dd['rescued_gb']} GB), "
          f"{dd['bad_sectors']} bad sectors, ETA ~{dd['eta_h']}h{auto}{fm_str}")

if __name__ == "__main__":
    main()
