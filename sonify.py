#!/usr/bin/env python3
"""
☽ Saint Charon — Vaporwave Sonification Engine v4.0
───────────────────────────────────────────────────────────────────────────
Data recovery → Vaporwave Music Generator (MIDI + OSC bridge)

Every variable from the extraction process drives the music:
  file types, sizes, hashes, directory depth, transfer speeds,
  bad sector bursts, carving rates, recovery percentage, eta trajectories,
  file name entropy, type rarity scores, and more.

Uses the same RecoveryData/MusicalMapper engine as vaporwave_synth.py
for consistent data-to-music parameter mapping.

MIDI CC MAP (channel 1, CC 20–79) — 60 continuous control parameters
MIDI NOTE EVENTS (channel 1) — 24+ event types triggered by recovery state
OSC ADDRESSES — full /saint_charon/* namespace
"""

import argparse, json, math, os, sys, time, threading, hashlib, random
from pathlib import Path
from collections import deque

# Import the shared data model from the audio synth
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from vaporwave_synth import RecoveryData, MusicalMapper, status_to_data
    SHARED_MODEL = True
except ImportError:
    SHARED_MODEL = False
    print("⚠  vaporwave_synth.py not found — using built-in mapper")

try:
    from pythonosc import udp_client
    OSC_AVAILABLE = True
except ImportError:
    OSC_AVAILABLE = False
    print("⚠  python-osc not found: OSC disabled  →  pip install python-osc")

try:
    import mido
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False
    print("⚠  mido not found: MIDI disabled  →  pip install mido python-rtmidi")

STATUS_FILE = "/tmp/status.json"

# ═══════════════════════════════════════════════════════════════════════════
# VAPORWAVE MUSICAL THEORY ENGINE
# ═══════════════════════════════════════════════════════════════════════════

SCALES = {
    "minor_penta":   [0, 3, 5, 7, 10],
    "dorian":        [0, 2, 3, 5, 7, 9, 10],
    "blues":         [0, 3, 5, 6, 7, 10],
    "natural_minor": [0, 2, 3, 5, 7, 8, 10],
    "phrygian":      [0, 1, 3, 5, 7, 8, 10],
    "mixolydian":    [0, 2, 4, 5, 7, 9, 10],
    "lydian":        [0, 2, 4, 6, 7, 9, 11],
    "japanese":      [0, 1, 5, 7, 8],
    "whole_tone":    [0, 2, 4, 6, 8, 10],
    "diminished":    [0, 2, 3, 5, 6, 8, 9, 11],
    "harmonic_min":  [0, 2, 3, 5, 7, 8, 11],
    "melodic_min":   [0, 2, 3, 5, 7, 9, 11],
}

CHORD_TYPES = {
    "maj7":     [0, 4, 7, 11],
    "min7":     [0, 3, 7, 10],
    "min9":     [0, 3, 7, 10, 14],
    "maj9":     [0, 4, 7, 11, 14],
    "sus4":     [0, 5, 7],
    "sus2":     [0, 2, 7],
    "add9":     [0, 4, 7, 14],
    "min11":    [0, 3, 7, 10, 14, 17],
    "dom7":     [0, 4, 7, 10],
    "dom9":     [0, 4, 7, 10, 14],
    "dim7":     [0, 3, 6, 9],
    "m7b5":     [0, 3, 6, 10],
    "quartal":  [0, 5, 10, 15],
    "cluster":  [0, 1, 6, 11],
}

PROGRESSIONS = {
    "dreamy_1":  [0, 3, 0, 2],
    "dreamy_2":  [0, 2, 4, 3],
    "nostalgia": [0, 4, 3, 0],
    "mallsoft":  [0, 1, 3, 2],
    "future":    [3, 2, 0, 4],
    "late_nite": [0, 4, 2, 3],
    "eccojams":  [0, 3, 4, 2],
    "808_beat":  [2, 0, 1, 3],
}

NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

CHORD_TYPES_LIST = list(CHORD_TYPES.keys())
PROGRESSIONS_LIST = list(PROGRESSIONS.keys())
SCALES_LIST = list(SCALES.keys())

CC = {
    "recovery_pct":        20, "transfer_rate":  21, "bad_sectors":    22,
    "bad_kb":              23, "carving_pct":    24, "total_files":    25,
    "files_jpg":           26, "files_mp4":      27, "files_png":      28,
    "files_mov":           29, "files_gif":      30, "eta_inverse":    31,
    "transfer_accel":      32, "running":        33, "chaos":          34,
    "vitality":            35, "corruption_density":36,"bad_sector_pulse":37,
    "file_burst":          38, "eta_confidence": 39,
    "jpg_ratio":           40, "video_ratio":    41, "image_video_balance":42,
    "type_entropy":        43, "type_rarity":    44, "jpg_trend":      45,
    "mp4_trend":           46, "png_trend":      47, "mov_trend":      48,
    "gif_trend":           49,
    "recovery_momentum":   50, "bad_density":    51, "rescue_efficiency":52,
    "scan_depth":          53, "data_flux":      54, "harmonic_tension":55,
    "dreaminess":          56, "tape_age":       57, "reverb_size":    58,
    "sidechain_pump":      59,
    "chord_root":          60, "chord_type":     61, "chord_progression":62,
    "scale_selector":      63, "arp_pattern":    64, "arp_rate":       65,
    "filter_cutoff":       66, "filter_resonance":67,"decay_time":     68,
    "swing_amount":        69,
    "eta_remaining_pct":   70, "peak_rate_ratio":71, "bad_cluster_density":72,
    "file_name_entropy":   73, "recovery_phase": 74, "data_density":   75,
    "vaporwave_index":     76, "midi_clock":     77, "phrase_position":78,
    "master_intensity":    79,
}

NOTE = {
    "bad_sector_hit":     36, "sector_cluster":    38, "rate_surge":    40,
    "rate_collapse":      41, "recovery_resume":   43, "recovery_stall":44,
    "platter_skip":       46,
    "file_milestone_1k":  48, "file_milestone_10k":50, "file_milestone_50k":52,
    "carving_complete":   55, "jpg_flood":         57, "mp4_burst":     59,
    "key_change_up":      60, "key_change_down":   61, "mode_shift_dorian":62,
    "mode_shift_blues":   64, "mode_shift_phrygian":65,"chord_prog_advance":67,
    "phrase_end":         69,
    "recovery_complete":  72, "all_complete":      76, "error_alert":   79,
}

def clamp(v, lo=0, hi=127):
    return max(lo, min(hi, int(v)))

def norm(v, lo, hi, out_lo=0, out_hi=127):
    if hi <= lo: return out_lo
    return clamp(out_lo + (v - lo) / (hi - lo) * (out_hi - out_lo))

def log_norm(v, cap, out_hi=127):
    if v <= 0: return 0
    return clamp(math.log1p(v) / math.log1p(cap) * out_hi)

def entropy(values):
    if not values or sum(values) == 0: return 0.0
    total = float(sum(values))
    probs = [v / total for v in values if v > 0]
    return -sum(p * math.log2(p) for p in probs)

def midi_to_freq(midi_note):
    return 440.0 * 2 ** ((midi_note - 69) / 12)

def scale_note(degree, octave, root_midi, scale_name):
    sc = SCALES.get(scale_name, SCALES["minor_penta"])
    idx = degree % len(sc)
    oct_shift = degree // len(sc)
    return root_midi + sc[idx] + (octave + oct_shift) * 12

def chord_notes(root_midi, chord_type_name, octave=0):
    intervals = CHORD_TYPES.get(chord_type_name, CHORD_TYPES["min7"])
    return [root_midi + i + octave * 12 for i in intervals]

def progression_chord(prog_name, step, root_midi, scale_name):
    prog = PROGRESSIONS.get(prog_name, PROGRESSIONS["dreamy_1"])
    sc = SCALES.get(scale_name, SCALES["minor_penta"])
    deg = prog[step % len(prog)]
    return root_midi + sc[deg % len(sc)]

class MusicalState:
    def __init__(self):
        self.root = 48
        self.scale = "minor_penta"
        self.progression = "dreamy_1"
        self.prog_step = 0
        self.chord_type = "min7"
        self.arp_pattern_idx = 0
        self.phrase_beats = 0
        self.bpm = 85
        self.intensity = 0.0
        self.dreaminess = 0.5
        self.tape_wow_depth = 0.0
        self.reverb_mix = 0.6
        self.sidechain_depth = 0.3
        self.lpf_cutoff = 0.3
        self.lpf_resonance = 0.1
        self.rate_history = deque(maxlen=60)
        self.bad_history = deque(maxlen=60)
        self.file_history = deque(maxlen=60)
        self._mapper = None   # shared MusicalMapper when available
        self._prev_data = None  # previous RecoveryData for delta computation

    def update_from_data(self, status, raw):
        dd = status.get("ddrescue") or {}
        fm = status.get("foremost") or {}
        byt = fm.get("by_type") or {}
        pct = raw.get("pct", 0)
        rate = raw.get("rate", 0)
        bad = raw.get("bad", 0)
        chaos = raw.get("chaos", 0)
        vitality = raw.get("vitality", 0)
        corruption = raw.get("corruption", 0)
        fm_files = raw.get("fm_files", 0)
        self.rate_history.append(rate)
        self.bad_history.append(bad)
        self.file_history.append(fm_files)
        self.bpm = int(70 + pct * 0.3 + vitality * 15 + min(rate / 20, 1) * 8)
        root_arc = [48, 50, 51, 53, 55, 57, 55, 53, 51, 50, 48]
        arc_idx = int(pct / 100 * (len(root_arc) - 1))
        self.root = root_arc[arc_idx] + (1 if chaos > 0.6 else 0)
        if chaos < 0.2: self.scale = "minor_penta"
        elif chaos < 0.35: self.scale = "dorian"
        elif chaos < 0.5: self.scale = "blues"
        elif chaos < 0.65: self.scale = "phrygian"
        elif chaos < 0.8: self.scale = "japanese"
        else: self.scale = "diminished"
        total = max(fm_files, 1)
        jpg_r = (byt.get("jpg", 0) or 0) / total
        video_r = ((byt.get("mp4", 0) or 0) + (byt.get("mov", 0) or 0)) / total
        gif_r = (byt.get("gif", 0) or 0) / total
        if jpg_r > 0.5: self.chord_type = "maj7"
        elif video_r > 0.4: self.chord_type = "min9"
        elif gif_r > 0.1: self.chord_type = "sus4"
        elif corruption > 0.3: self.chord_type = "dim7"
        elif chaos > 0.6: self.chord_type = "m7b5"
        else: self.chord_type = "min7"
        if jpg_r > 0.6: self.progression = "nostalgia"
        elif video_r > 0.5: self.progression = "late_nite"
        elif gif_r > 0.05: self.progression = "eccojams"
        elif chaos > 0.5: self.progression = "mallsoft"
        elif vitality > 0.7: self.progression = "future"
        else: self.progression = "dreamy_1"
        type_counts = [byt.get("jpg",0)or 0, byt.get("mp4",0)or 0, byt.get("png",0)or 0, byt.get("mov",0)or 0, byt.get("gif",0)or 0]
        type_ent = entropy(type_counts)
        self.arp_pattern_idx = int(type_ent / max(2.5, 0.01) * 5) % 6
        self.dreaminess = max(0, 1 - chaos * 0.9)
        self.tape_wow_depth = chaos * 0.4 + corruption * 0.3
        self.reverb_mix = 0.4 + self.dreaminess * 0.5
        self.sidechain_depth = 0.1 + vitality * 0.5
        self.lpf_cutoff = 0.2 + pct / 100 * 0.7
        self.lpf_resonance = 0.05 + chaos * 0.5
        self.intensity = 0.2 + vitality * 0.6 + (pct / 100) * 0.2
        self.phrase_beats += 1
        if self.phrase_beats % 64 == 0:
            self.prog_step = (self.prog_step + 1) % 4

        # ── Override with shared model when available ──
        if SHARED_MODEL:
            try:
                data_obj = status_to_data(status, self._prev_data)
                mapper = MusicalMapper(data_obj)
                self.root = mapper.root_midi
                self.scale = mapper.scale
                self.progression = mapper.prog_name
                self.chord_type = mapper.chord_quality
                self.bpm = mapper.bpm
                self.dreaminess = data_obj.dreaminess
                self.tape_wow_depth = mapper.tape_wow_depth
                self.reverb_mix = mapper.reverb_mix
                self.sidechain_depth = mapper.sidechain_depth
                self.lpf_cutoff = mapper.lpf_cutoff_ratio
                self.lpf_resonance = mapper.lpf_resonance
                self.intensity = data_obj.vitality * 0.6 + (data_obj.pct / 100) * 0.4
                self._mapper = mapper
                self._prev_data = data_obj
            except Exception:
                pass  # fall back to local calculations

MUS = MusicalState()
_gcc = {}
_prev_raw = {}
_beat_counter = 0


def read_status(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}

def compute(status, prev):
    dd  = status.get("ddrescue") or {}
    fm  = status.get("foremost") or {}
    byt = fm.get("by_type") or {}
    pdd = (prev.get("ddrescue") or {}) if prev else {}
    pfm = (prev.get("foremost") or {}) if prev else {}

    pct        = float(dd.get("pct") or 0)
    rate       = float(dd.get("rate_gb_h") or 0)
    bad        = int(dd.get("bad_sectors") or 0)
    bad_kb     = int(dd.get("bad_kb") or 0)
    rescued_gb = float(dd.get("rescued_gb") or 0)
    total_gb   = float(dd.get("total_gb") or 400)
    eta_h      = float(dd.get("eta_h") or 0)
    dd_run     = bool(dd.get("running", False))
    elapsed    = float(dd.get("elapsed_s") or 0)

    fm_pct   = float(fm.get("pct") or 0)
    fm_files = int(fm.get("total_files") or 0)
    fm_run   = bool(fm.get("running", False))
    jpg = int(byt.get("jpg") or 0); mp4 = int(byt.get("mp4") or 0)
    png = int(byt.get("png") or 0); mov = int(byt.get("mov") or 0)
    gif = int(byt.get("gif") or 0); avi = int(byt.get("avi") or 0)
    wav = int(byt.get("wav") or 0); pdf = int(byt.get("pdf") or 0)
    zipf= int(byt.get("zip") or 0)

    prev_bad    = int(pdd.get("bad_sectors") or 0)
    prev_rate   = float(pdd.get("rate_gb_h") or 0)
    prev_pct    = float(pdd.get("pct") or 0)
    prev_elapsed= float(pdd.get("elapsed_s") or 0)
    prev_files  = int(pfm.get("total_files") or 0)
    prev_fmpct  = float(pfm.get("pct") or 0)
    prev_jpg = int((pfm.get("by_type") or {}).get("jpg") or 0)
    prev_mp4 = int((pfm.get("by_type") or {}).get("mp4") or 0)
    prev_png = int((pfm.get("by_type") or {}).get("png") or 0)
    prev_mov = int((pfm.get("by_type") or {}).get("mov") or 0)
    prev_gif = int((pfm.get("by_type") or {}).get("gif") or 0)

    total_fm = max(fm_files, 1)
    corruption = bad_kb / max(rescued_gb * 1024, 1)
    vitality   = min(rate / 20.0, 1.0)
    chaos = (log_norm(bad, 500) / 127 * 0.40 + max(0, 1 - vitality) * 0.30 + min(corruption * 6, 1) * 0.30)

    rate_accel = 0.0
    if prev_rate > 0 and rate > 0:
        rate_accel = (rate - prev_rate) / max(prev_rate, 0.01)

    eta_conf = 0.5
    if abs(eta_h - float(pdd.get("eta_h") or eta_h)) < eta_h * 0.1:
        eta_conf = 0.8

    efficiency = 0.0
    if elapsed > 0:
        efficiency = rescued_gb / (elapsed / 3600)

    peak_ratio = 0.5
    if MUS.rate_history and len(MUS.rate_history) > 0:
        peak_rate = max(MUS.rate_history)
        peak_ratio = rate / max(peak_rate, 0.1)

    jpg_ratio  = jpg / max(total_fm, 1)
    video_ratio= (mp4 + mov) / max(total_fm, 1)
    img_vid_balance = min(jpg_ratio / max(video_ratio, 0.01) / 5, 1)

    all_types = [jpg, mp4, png, mov, gif, avi, wav, pdf, zipf]
    type_ent = entropy(all_types) / 3.17
    type_rarity = min(1.0, (gif + wav + pdf + zipf + avi) / max(total_fm, 1) * 5)

    jpg_trend = (jpg - prev_jpg) / max(jpg, 1)
    mp4_trend = (mp4 - prev_mp4) / max(mp4, 1)
    png_trend = (png - prev_png) / max(png, 1)
    mov_trend = (mov - prev_mov) / max(mov, 1)
    gif_trend = (gif - prev_gif) / max(gif, 1)

    recovery_momentum = (pct - prev_pct) / max(prev_pct, 0.01) if prev_pct > 0 else 0
    recovery_momentum = max(-1, min(1, recovery_momentum))

    data_flux = min(1, (rate / 20 * 0.4 + abs(recovery_momentum) * 0.3 + min(fm_files - prev_files, 500) / 500 * 0.3))
    harmonic_tension = chaos * 0.6 + corruption * 0.4
    dreaminess = max(0, 1 - harmonic_tension)

    bad_cluster = 0.0
    if bad > 10 and prev_bad > 10:
        bad_cluster = min(1.0, (bad - prev_bad) / max(bad, 1) * 3)

    new_bad     = max(0, bad - prev_bad)
    new_files   = max(0, fm_files - prev_files)
    delta_jpg   = max(0, jpg - prev_jpg)
    delta_mp4   = max(0, mp4 - prev_mp4)
    rate_2x     = rate > max(prev_rate * 2.0, 1) and prev_rate > 0.5
    rate_half   = rate < prev_rate * 0.5 and prev_rate > 2 and rate < prev_rate
    rate_stall  = rate < 0.1 and prev_rate > 1
    rate_resume = rate > 1 and prev_rate < 0.1

    prev_1k  = prev_files // 1000;  now_1k   = fm_files // 1000
    prev_10k = prev_files // 10000; now_10k  = fm_files // 10000
    prev_50k = prev_files // 50000; now_50k  = fm_files // 50000

    cc_vals = {
        "recovery_pct":       norm(pct, 0, 100),
        "transfer_rate":      norm(rate, 0, 20),
        "bad_sectors":        log_norm(bad, 500),
        "bad_kb":             log_norm(bad_kb, 10000),
        "carving_pct":        norm(fm_pct, 0, 100),
        "total_files":        log_norm(fm_files, 500000),
        "files_jpg":          log_norm(jpg, 200000),
        "files_mp4":          log_norm(mp4, 50000),
        "files_png":          log_norm(png, 100000),
        "files_mov":          log_norm(mov, 20000),
        "files_gif":          log_norm(gif, 10000),
        "eta_inverse":        norm(eta_h, 0, 72, 127, 0),
        "transfer_accel":     clamp(63 + rate_accel * 64),
        "running":            127 if (dd_run or fm_run) else 0,
        "chaos":              clamp(chaos * 127),
        "vitality":           clamp(vitality * 127),
        "corruption_density": clamp(min(corruption * 200, 127)),
        "bad_sector_pulse":   clamp(new_bad * 25) if new_bad else 0,
        "file_burst":         log_norm(new_files, 1000),
        "eta_confidence":     clamp(eta_conf * 127),
        "jpg_ratio":          clamp(jpg_ratio * 127),
        "video_ratio":        clamp(video_ratio * 127),
        "image_video_balance":clamp(img_vid_balance * 127),
        "type_entropy":       clamp(type_ent * 127),
        "type_rarity":        clamp(type_rarity * 127),
        "jpg_trend":          clamp(63 + jpg_trend * 63),
        "mp4_trend":          clamp(63 + mp4_trend * 63),
        "png_trend":          clamp(63 + png_trend * 63),
        "mov_trend":          clamp(63 + mov_trend * 63),
        "gif_trend":          clamp(63 + gif_trend * 63),
        "recovery_momentum":  clamp(63 + recovery_momentum * 63),
        "bad_density":        clamp(log_norm(bad / max(rescued_gb, 0.01), 50) if rescued_gb > 0 else 0),
        "rescue_efficiency":  clamp(norm(efficiency, 0, 10)),
        "scan_depth":         clamp(fm_pct / 100 * 127),
        "data_flux":          clamp(data_flux * 127),
        "harmonic_tension":   clamp(harmonic_tension * 127),
        "dreaminess":         clamp(dreaminess * 127),
        "tape_age":           clamp(MUS.tape_wow_depth * 127),
        "reverb_size":        clamp(MUS.reverb_mix * 127),
        "sidechain_pump":     clamp(MUS.sidechain_depth * 127),
        "chord_root":         MUS.root,
        "chord_type":         clamp(CHORD_TYPES_LIST.index(MUS.chord_type) / max(len(CHORD_TYPES_LIST)-1,1) * 127 if MUS.chord_type in CHORD_TYPES_LIST else 64),
        "chord_progression":  clamp(PROGRESSIONS_LIST.index(MUS.progression) / max(len(PROGRESSIONS_LIST)-1,1) * 127 if MUS.progression in PROGRESSIONS_LIST else 64),
        "scale_selector":     clamp(SCALES_LIST.index(MUS.scale) / max(len(SCALES_LIST)-1,1) * 127 if MUS.scale in SCALES_LIST else 64),
        "arp_pattern":        clamp(MUS.arp_pattern_idx / 5 * 127),
        "arp_rate":           clamp(63 + vitality * 63),
        "filter_cutoff":      clamp(MUS.lpf_cutoff * 127),
        "filter_resonance":   clamp(MUS.lpf_resonance * 127),
        "decay_time":         clamp(127 - vitality * 100),
        "swing_amount":       clamp(chaos * 127),
        "eta_remaining_pct":  clamp(norm(eta_h, 0, 72)),
        "peak_rate_ratio":    clamp(peak_ratio * 127),
        "bad_cluster_density":clamp(bad_cluster * 127),
        "file_name_entropy":  clamp(type_ent * 127),
        "recovery_phase":     clamp(pct / 100 * 127),
        "data_density":       clamp(norm(rescued_gb / max(total_gb, 0.01), 0, 1)),
        "vaporwave_index":    clamp(dreaminess * 80 + vitality * 47),
        "midi_clock":         clamp((_beat_counter % 128) / 128 * 127),
        "phrase_position":    clamp((MUS.phrase_beats % 64) / 64 * 127),
        "master_intensity":   clamp(MUS.intensity * 127),
    }

    osc_vals = {
        "/saint_charon/recovery/pct":              pct / 100,
        "/saint_charon/recovery/rate":             rate,
        "/saint_charon/recovery/bad_sectors":      float(bad),
        "/saint_charon/recovery/bad_kb":           float(bad_kb),
        "/saint_charon/recovery/running":          float(int(dd_run)),
        "/saint_charon/recovery/eta_h":            eta_h,
        "/saint_charon/recovery/vitality":         vitality,
        "/saint_charon/recovery/chaos":            chaos,
        "/saint_charon/recovery/efficiency":       efficiency,
        "/saint_charon/recovery/momentum":         recovery_momentum,
        "/saint_charon/carving/pct":               fm_pct / 100,
        "/saint_charon/carving/files":             float(fm_files),
        "/saint_charon/carving/jpg":               float(jpg),
        "/saint_charon/carving/mp4":               float(mp4),
        "/saint_charon/carving/png":               float(png),
        "/saint_charon/carving/mov":               float(mov),
        "/saint_charon/carving/gif":               float(gif),
        "/saint_charon/carving/running":           float(int(fm_run)),
        "/saint_charon/derived/corruption":        min(corruption, 1.0),
        "/saint_charon/derived/file_burst":        min(new_files / 1000, 1.0),
        "/saint_charon/derived/type_entropy":      type_ent,
        "/saint_charon/derived/type_rarity":       type_rarity,
        "/saint_charon/derived/jpg_ratio":         jpg_ratio,
        "/saint_charon/derived/video_ratio":       video_ratio,
        "/saint_charon/derived/data_flux":         data_flux,
        "/saint_charon/music/root":                float(MUS.root),
        "/saint_charon/music/bpm":                 float(MUS.bpm),
        "/saint_charon/music/scale":               MUS.scale,
        "/saint_charon/music/chord_type":          MUS.chord_type,
        "/saint_charon/music/progression":         MUS.progression,
        "/saint_charon/music/intensity":           MUS.intensity,
        "/saint_charon/music/dreaminess":          dreaminess,
        "/saint_charon/music/tape_wow":            MUS.tape_wow_depth,
        "/saint_charon/music/reverb_mix":          MUS.reverb_mix,
        "/saint_charon/music/sidechain":           MUS.sidechain_depth,
        "/saint_charon/music/lpf_cutoff":          MUS.lpf_cutoff,
        "/saint_charon/music/beat":                float(_beat_counter % 128),
        "/saint_charon/music/phrase":              float(MUS.phrase_beats % 64),
    }

    events = {
        "new_bad":          new_bad,
        "sector_cluster":   new_bad >= 5,
        "rate_surge":       rate_2x,
        "rate_collapse":    rate_half,
        "recovery_stall":   rate_stall,
        "recovery_resume":  rate_resume,
        "platter_skip":     new_bad >= 1 and rate < 0.5 and dd_run,
        "file_milestone_1k": now_1k > prev_1k and fm_files > 0,
        "file_milestone_10k":now_10k > prev_10k and fm_files > 0,
        "file_milestone_50k":now_50k > prev_50k and fm_files > 0,
        "carving_complete": fm_pct >= 99.9 and prev_fmpct < 99.9,
        "jpg_flood":        delta_jpg >= 100,
        "mp4_burst":        delta_mp4 >= 50,
        "key_change_up":    recovery_momentum > 0.5 and pct > 10,
        "key_change_down":  chaos > 0.7,
        "mode_shift_dorian": jpg_ratio > 0.55 and chaos < 0.4,
        "mode_shift_blues": corruption > 0.4,
        "mode_shift_phrygian": chaos > 0.75,
        "chord_prog_advance":MUS.phrase_beats % 64 == 0,
        "phrase_end":       MUS.phrase_beats % 64 == 63,
        "recovery_complete":pct >= 99.9 and prev_pct < 99.9,
        "all_complete":     pct >= 99.9 and fm_pct >= 99.9,
        "error_alert":      bad > 100 and rate < 0.3 and dd_run,
    }

    raw = dict(pct=pct, rate=rate, bad=bad, bad_kb=bad_kb,
               fm_pct=fm_pct, fm_files=fm_files,
               chaos=chaos, vitality=vitality, corruption=corruption,
               efficiency=efficiency, recovery_momentum=recovery_momentum,
               data_flux=data_flux, type_entropy=type_ent,
               jpg=jpg, mp4=mp4, png=png, mov=mov, gif=gif)
    return cc_vals, osc_vals, events, raw


def build_chord_events(midi_out, ch=0):
    root_note = progression_chord(MUS.progression, MUS.prog_step, MUS.root, MUS.scale)
    notes = chord_notes(root_note, MUS.chord_type, octave=0)
    for i, note in enumerate(notes):
        vel = clamp(40 + MUS.intensity * 50 - i * 6)
        if midi_out:
            try:
                midi_out.send(mido.Message("note_on", channel=ch, note=clamp(note, 0, 127), velocity=vel))
                def off(n=note, v=vel):
                    time.sleep(0.05 + i * 0.02)
                    try:
                        midi_out.send(mido.Message("note_off", channel=ch, note=clamp(n, 0, 127), velocity=0))
                    except: pass
                threading.Thread(target=off, daemon=True).start()
            except: pass


class Sonifier:
    def __init__(self, args):
        self.args = args
        self.osc = None
        self.midi_out = None
        self.prev_status = {}
        self.prev_cc = {}
        self.tick_count = 0
        if OSC_AVAILABLE and not args.no_osc:
            self.osc = udp_client.SimpleUDPClient(args.osc_host, args.osc_port)
            print(f"✅ OSC  →  {args.osc_host}:{args.osc_port}")
        if MIDI_AVAILABLE and not args.no_midi:
            try:
                self.midi_out = mido.open_output(args.midi_port, virtual=True)
                print(f"✅ MIDI →  virtual port '{args.midi_port}'")
            except Exception as e:
                print(f"⚠  MIDI: {e}")

    def cc(self, num, val, ch=0):
        if self.midi_out:
            try:
                self.midi_out.send(mido.Message("control_change", channel=ch, control=num, value=clamp(val)))
            except: pass

    def note(self, num, vel=80, dur=0.15, ch=0):
        if self.midi_out:
            try:
                self.midi_out.send(mido.Message("note_on", channel=ch, note=clamp(num, 0, 127), velocity=clamp(vel)))
                def _off():
                    time.sleep(dur)
                    try:
                        self.midi_out.send(mido.Message("note_off", channel=ch, note=clamp(num, 0, 127), velocity=0))
                    except: pass
                threading.Thread(target=_off, daemon=True).start()
            except: pass

    def osc_send(self, addr, val):
        if self.osc:
            try:
                self.osc.send_message(addr, float(val) if not isinstance(val, str) else val)
            except: pass

    def tick(self, status):
        global _beat_counter, _gcc
        cc_vals, osc_vals, events, raw = compute(status, self.prev_status)
        MUS.update_from_data(status, raw)
        _beat_counter += 1

        for name, num in CC.items():
            val = cc_vals.get(name, 0)
            prev = self.prev_cc.get(name, -1)
            if prev != val:
                self.cc(num, val)
                self.prev_cc[name] = val

        for addr, val in osc_vals.items():
            self.osc_send(addr, val)

        # ── Events ──
        if events["new_bad"]:
            sev = clamp(35 + events["new_bad"] * 10)
            self.note(NOTE["bad_sector_hit"], sev, dur=0.22)
            self.osc_send("/saint_charon/event/bad_sector", events["new_bad"])
            if events["sector_cluster"]:
                time.sleep(0.02)
                self.note(NOTE["sector_cluster"], sev + 10, dur=0.35)
                cluster = [MUS.root, MUS.root + 1, MUS.root + 6, MUS.root + 8]
                threading.Thread(target=lambda: [self.note(n, 50, 0.3) or time.sleep(0.015) for n in cluster], daemon=True).start()
                self.osc_send("/saint_charon/event/sector_cluster", 1)

        if events["rate_surge"]:
            self.note(NOTE["rate_surge"], 68, dur=0.12)
            for i in [0, 2, 4, 7]:
                self.note(MUS.root + i + 12, 55, dur=0.1)
                time.sleep(0.03)
            self.osc_send("/saint_charon/event/rate_surge", 1.0)

        if events["rate_collapse"]:
            self.note(NOTE["rate_collapse"], 48, dur=0.2)
            for i in [7, 4, 2, 0]:
                self.note(MUS.root + i, 42, dur=0.15)
                time.sleep(0.04)
            self.osc_send("/saint_charon/event/rate_collapse", 1.0)

        if events["recovery_stall"]:
            self.note(NOTE["recovery_stall"], 35, dur=0.5)
            self.osc_send("/saint_charon/event/stall", 1.0)

        if events["recovery_resume"]:
            self.note(NOTE["recovery_resume"], 72, dur=0.15)
            self.osc_send("/saint_charon/event/resume", 1.0)

        if events["platter_skip"]:
            self.note(NOTE["platter_skip"], 55, dur=0.08)
            self.osc_send("/saint_charon/event/platter_skip", 1.0)

        if events["file_milestone_1k"]:
            self.note(NOTE["file_milestone_1k"], 60, dur=0.1)
            sc = SCALES.get(MUS.scale, SCALES["minor_penta"])
            for i in range(6):
                self.note(scale_note(i % len(sc), 2, MUS.root, MUS.scale), 40 + i * 8, dur=0.08)
                time.sleep(0.025)
            self.osc_send("/saint_charon/event/file_milestone_1k", raw.get("fm_files", 0))

        if events["file_milestone_10k"]:
            self.note(NOTE["file_milestone_10k"], 80, dur=0.15)
            for i in [0, 2, 4, 7, 11]:
                self.note(MUS.root + i + 24, 55, dur=0.2)
                time.sleep(0.04)
            self.osc_send("/saint_charon/event/file_milestone_10k", raw.get("fm_files", 0))

        if events["file_milestone_50k"]:
            self.note(NOTE["file_milestone_50k"], 100, dur=0.2)
            self.osc_send("/saint_charon/event/file_milestone_50k", raw.get("fm_files", 0))

        if events["jpg_flood"]:
            self.note(NOTE["jpg_flood"], 75, dur=0.12)
            self.osc_send("/saint_charon/event/jpg_flood", 1.0)

        if events["mp4_burst"]:
            self.note(NOTE["mp4_burst"], 70, dur=0.14)
            self.osc_send("/saint_charon/event/mp4_burst", 1.0)

        if events["key_change_up"]:
            self.note(NOTE["key_change_up"], 65, dur=0.18)
            self.osc_send("/saint_charon/event/key_change_up", 1.0)

        if events["key_change_down"]:
            self.note(NOTE["key_change_down"], 55, dur=0.22)
            self.osc_send("/saint_charon/event/key_change_down", 1.0)

        if events["mode_shift_dorian"]:
            self.note(NOTE["mode_shift_dorian"], 58, dur=0.15)
            self.osc_send("/saint_charon/event/mode_shift", "dorian")

        if events["mode_shift_blues"]:
            self.note(NOTE["mode_shift_blues"], 62, dur=0.15)
            self.osc_send("/saint_charon/event/mode_shift", "blues")

        if events["mode_shift_phrygian"]:
            self.note(NOTE["mode_shift_phrygian"], 50, dur=0.2)
            self.osc_send("/saint_charon/event/mode_shift", "phrygian")

        if events["chord_prog_advance"]:
            self.note(NOTE["chord_prog_advance"], 45, dur=0.08)
            threading.Thread(target=lambda: build_chord_events(self.midi_out), daemon=True).start()
            self.osc_send("/saint_charon/event/chord_prog_advance", float(MUS.prog_step))

        if events["phrase_end"]:
            self.note(NOTE["phrase_end"], 40, dur=0.05)
            self.osc_send("/saint_charon/event/phrase_end", 1.0)

        if events["carving_complete"]:
            self.note(NOTE["carving_complete"], 100, dur=0.4)
            time.sleep(0.05)
            self.note(NOTE["carving_complete"] + 4, 90, dur=0.45)
            time.sleep(0.05)
            self.note(NOTE["carving_complete"] + 7, 85, dur=0.5)
            self.osc_send("/saint_charon/event/carving_complete", 1.0)

        if events["recovery_complete"]:
            for n in [NOTE["recovery_complete"], NOTE["recovery_complete"] + 4, NOTE["recovery_complete"] + 7, NOTE["recovery_complete"] + 12]:
                self.note(n, 110, dur=0.6)
                time.sleep(0.06)
            self.osc_send("/saint_charon/event/recovery_complete", 1.0)

        if events["all_complete"]:
            root = NOTE["all_complete"]
            for n in [root, root + 3, root + 7, root + 10, root + 12, root + 15]:
                self.note(n, 100, dur=0.8)
                time.sleep(0.04)
            self.osc_send("/saint_charon/event/all_complete", 1.0)

        if events["error_alert"]:
            self.note(NOTE["error_alert"], 80, dur=0.08)
            self.note(NOTE["error_alert"] + 1, 75, dur=0.06)
            self.note(NOTE["error_alert"] + 6, 70, dur=0.1)
            self.osc_send("/saint_charon/event/error_alert", 1.0)

        self.prev_status = status

        bar = "█" * int(raw["pct"] / 5) + "░" * (20 - int(raw["pct"] / 5))
        if self.args.verbose:
            print(f"\n[{time.strftime('%H:%M:%S')}]  ☽ tick {self.tick_count}")
            print(f"  rec {raw['pct']:.1f}%  rate {raw['rate']:.2f} GB/h  bad {raw['bad']}")
            print(f"  carv {raw['fm_pct']:.1f}%  files {raw['fm_files']}")
            print(f"  ♫ {NOTE_NAMES[MUS.root%12]} {MUS.scale}@{MUS.bpm}BPM  {MUS.chord_type}")
            print(f"  chaos {raw['chaos']:.3f}  dreaminess {MUS.dreaminess:.2f}  flux {raw['data_flux']:.3f}")
            if events["new_bad"]:
                print(f"  ⚠  NEW BAD: +{events['new_bad']}")
        else:
            nn = NOTE_NAMES[MUS.root % 12]
            print(f"\r☽ [{bar}] {raw['pct']:.1f}%  ♫{nn} {MUS.scale}@{MUS.bpm}BPM  "
                  f"rate:{raw['rate']:.1f}  bad:{raw['bad']}  files:{raw['fm_files']}  "
                  f"☁{MUS.dreaminess:.2f}", end="", flush=True)
        self.tick_count += 1


def sim_status(t):
    pct = min(99.9, (t % 450) / 4.5 + math.sin(t * 0.03) * 3)
    base_rate = 3 + math.sin(t * 0.15) * 2.0
    spike = 8 if int(t) % 43 == 0 else 0
    dip = -2.5 if int(t) % 67 == 0 else 0
    rate = max(0, base_rate + spike + dip + math.sin(t * 0.9) * 0.6 + math.sin(t * 2.7) * 0.3 + math.sin(t * 5.1) * 0.15)
    base_bad = max(0, int(5 + math.sin(t * 0.05) * 3 + (6 if int(t) % 53 == 0 else 0) + (14 if int(t) % 127 == 0 else 0)))
    bad_kb = base_bad * 4
    rescued_gb = round(pct * 3.8 + math.sin(t * 0.1) * 0.5, 2)
    total_gb = 400
    fm_pct = min(98, pct * 0.75 + 5)
    fm_files = max(0, int(pct * 220 + math.sin(t * 0.4) * 400 + (500 if int(t) % 37 == 0 else 0) + (200 if int(t) % 89 == 0 else 0)))
    remaining = max(0, 100 - pct)
    eta_h = round(remaining / max(rate, 0.01), 1)
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ddrescue": {
            "pct": round(pct, 2), "rate_gb_h": round(rate, 3),
            "bad_sectors": base_bad, "bad_kb": bad_kb,
            "rescued_gb": rescued_gb, "total_gb": total_gb,
            "elapsed_s": int(t % 3600 * 100 + t * 3600 * 0.1),
            "eta_h": eta_h, "running": pct < 99,
        },
        "foremost": {
            "pct": round(fm_pct, 2), "total_files": fm_files,
            "total_size": f"{fm_files * 2.3:.1f} MB",
            "running": fm_pct < 85,
            "by_type": {
                "jpg": int(fm_files * (0.45 + math.sin(t * 0.08) * 0.15)),
                "mp4": int(fm_files * (0.12 + math.cos(t * 0.12) * 0.05)),
                "png": int(fm_files * (0.14 + math.sin(t * 0.1) * 0.04)),
                "mov": int(fm_files * (0.06 + math.cos(t * 0.15) * 0.03)),
                "gif": int(fm_files * (0.04 + math.sin(t * 0.18) * 0.02)),
                "avi": int(fm_files * 0.02),
                "wav": int(fm_files * 0.015),
                "pdf": int(fm_files * 0.01),
                "zip": int(fm_files * 0.005),
            },
        },
    }


def main():
    p = argparse.ArgumentParser(description="☽ Saint Charon — Vaporwave Sonification Engine v3",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--osc-host", default="127.0.0.1", help="OSC host")
    p.add_argument("--osc-port", default=9000, type=int, help="OSC port")
    p.add_argument("--midi-port", default="Saint Charon", help="Virtual MIDI port name")
    p.add_argument("--status", default=STATUS_FILE, help="Path to status.json")
    p.add_argument("--interval", default=2.0, type=float, help="Poll interval seconds")
    p.add_argument("--no-osc", action="store_true", help="Disable OSC")
    p.add_argument("--no-midi", action="store_true", help="Disable MIDI")
    p.add_argument("--sim", action="store_true", help="Simulation mode")
    p.add_argument("--verbose", action="store_true", help="Verbose output")
    args = p.parse_args()

    print("☽ Saint Charon — Vaporwave Sonification Engine v3.0")
    print(f"   status: {args.status}  poll: {args.interval}s  mode: {'SIM' if args.sim else 'LIVE'}")
    print()

    s = Sonifier(args)
    if not s.osc and not s.midi_out:
        print("❌ No outputs. Install: pip install python-osc mido python-rtmidi")
        sys.exit(1)

    print("Running — Ctrl+C to stop\n")
    t0 = time.time()
    try:
        while True:
            t = time.time() - t0
            status = sim_status(t) if args.sim else read_status(args.status)
            s.tick(status)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n\n☽ stopped gracefully.")
        if s.midi_out:
            for ch in range(16):
                try: s.midi_out.send(mido.Message("control_change", channel=ch, control=123, value=0))
                except: pass
            s.midi_out.close()

if __name__ == "__main__":
    main()
