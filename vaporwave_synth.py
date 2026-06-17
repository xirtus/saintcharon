#!/usr/bin/env python3
"""
☽ vaporwave_synth.py — Saint Charon Vaporwave Audio Engine v4.0
═══════════════════════════════════════════════════════════════════════════
Generative vaporwave music entirely driven by data recovery metrics.

Every parameter of the music is informed by the extraction process:
  recovery%, transfer rate, bad sectors, carving activity, file type ratios,
  directory depth, type entropy, corruption density, ETA trajectories,
  transfer acceleration, file bursts, name entropy, hash distributions, etc.

Engine features:
  • Triple-oscillator detuned pad engine with chorus + slow filter sweeps
  • DX7-style FM bass with resonant filter and slide/glide
  • Full 808 drum synthesizer — kick, snare, hats, clap, rim, toms, cymbal
  • Probability-driven drum patterns with ghost notes and random fills
  • Plate/hall reverb, ping-pong tape delay, chorus, phaser
  • Tape saturation, wow/flutter, vinyl crackle, bitcrush lo-fi
  • Sidechain compressor (classic vaporwave pump)
  • Section-based arrangement: intro → verse → chorus → bridge → outro
  • Mastering chain: EQ → saturation → compression → lookahead limiter
  • All parameters continuously derived from live recovery data
  • Random seed derived from data for reproducible stochastic variation

Output: 48kHz/24bit float → 16bit WAV stereo (always plays loud)

QUICK START:
    python3 vaporwave_synth.py --sim --out vaporwave_dream.wav
    python3 vaporwave_synth.py --status /tmp/status.json --out recovery_beats.wav
    python3 vaporwave_synth.py --sim --length 180 --bpm 80 --seed 42 --out mallsoft.wav
"""

import argparse, json, math, os, random, struct, sys, time, wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import deque

try:
    import numpy as np
    NUMPY = True
except ImportError:
    NUMPY = False
    print("❌ numpy is required for audio rendering. Install: pip install numpy")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

SAMPLE_RATE = 48000
CHANNELS = 2
PI = math.pi
TAU = 2 * PI
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# ═══════════════════════════════════════════════════════════════════════════
# MUSIC THEORY — Expanded vaporwave palette
# ═══════════════════════════════════════════════════════════════════════════

SCALES = {
    "minor_penta":      [0, 3, 5, 7, 10],
    "major_penta":      [0, 2, 4, 7, 9],
    "dorian":           [0, 2, 3, 5, 7, 9, 10],
    "blues":            [0, 3, 5, 6, 7, 10],
    "natural_minor":    [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor":   [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor":    [0, 2, 3, 5, 7, 9, 11],
    "phrygian":         [0, 1, 3, 5, 7, 8, 10],
    "mixolydian":       [0, 2, 4, 5, 7, 9, 10],
    "lydian":           [0, 2, 4, 6, 7, 9, 11],
    "japanese":         [0, 1, 5, 7, 8],
    "whole_tone":       [0, 2, 4, 6, 8, 10],
    "diminished":       [0, 2, 3, 5, 6, 8, 9, 11],
    "locrian":          [0, 1, 3, 5, 6, 8, 10],
    "egyptian":         [0, 2, 5, 7, 10],
    "hirajoshi":        [0, 2, 3, 7, 8],
}

CHORD_QUALITIES = {
    "maj7":     [0, 4, 7, 11],
    "min7":     [0, 3, 7, 10],
    "min9":     [0, 3, 7, 10, 14],
    "maj9":     [0, 4, 7, 11, 14],
    "min11":    [0, 3, 7, 10, 14, 17],
    "maj13":    [0, 4, 7, 11, 14, 21],
    "sus4":     [0, 5, 7],
    "sus2":     [0, 2, 7],
    "add9":     [0, 4, 7, 14],
    "dom7":     [0, 4, 7, 10],
    "dom9":     [0, 4, 7, 10, 14],
    "dim7":     [0, 3, 6, 9],
    "m7b5":     [0, 3, 6, 10],
    "aug7":     [0, 4, 8, 10],
    "quartal":  [0, 5, 10, 15],
    "cluster":  [0, 1, 6, 11],
    "dreams":   [0, 4, 7, 14, 21],
    "mallsoft": [0, 3, 7, 10, 17],
}

PROGRESSIONS = {
    "dreamy_1":     [(0, "min7"), (3, "min7"), (0, "min9"), (2, "maj7")],
    "dreamy_2":     [(0, "min9"), (2, "maj7"), (4, "min7"), (3, "min7")],
    "nostalgia":    [(0, "min7"), (4, "min7"), (3, "min7"), (0, "maj7")],
    "mallsoft":     [(0, "min7"), (1, "maj7"), (3, "min7"), (2, "maj7")],
    "future_funk":  [(3, "min9"), (2, "maj7"), (0, "min7"), (4, "min7")],
    "late_nite":    [(0, "min9"), (4, "sus4"), (2, "maj9"), (3, "min7")],
    "eccojams":     [(0, "maj7"), (3, "min7"), (4, "maj7"), (2, "min9")],
    "808_beat":     [(2, "maj7"), (0, "min7"), (1, "maj7"), (3, "min7")],
    "crystal_dawn": [(0, "maj9"), (4, "min11"), (3, "dom9"), (0, "dreams")],
    "vapor_drip":   [(0, "min11"), (3, "maj13"), (2, "min9"), (1, "dom7")],
    "liminal":      [(0, "sus4"), (2, "add9"), (4, "sus2"), (3, "maj7")],
    "plaza":        [(0, "maj7"), (3, "dom7"), (4, "min7"), (2, "maj9")],
    "eternal_dusk": [(0, "dreams"), (4, "min7"), (3, "mallsoft"), (0, "min9")],
    "broken_drive": [(0, "m7b5"), (3, "dim7"), (2, "min7"), (4, "aug7")],
    "corruption":   [(0, "cluster"), (3, "m7b5"), (1, "dim7"), (2, "quartal")],
    "hex_sunset":   [(0, "sus2"), (3, "add9"), (4, "maj9"), (2, "min11")],
}

BASS_PATTERNS = {
    "simple":     [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    "offbeat":    [1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1],
    "walking":    [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0],
    "syncopated": [1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0],
    "funky":      [1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0],
    "ghost":      [1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0],
}

def midi_to_freq(note: float) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)

def freq_to_midi(freq: float) -> float:
    return 69 + 12 * math.log2(freq / 440.0)

def note_name(note: int) -> str:
    return f"{NOTE_NAMES[note % 12]}{note // 12 - 1}"

def scale_degree_to_midi(degree: int, root_midi: int, scale_name: str, octave: int = 0) -> int:
    sc = SCALES.get(scale_name, SCALES["minor_penta"])
    idx = degree % len(sc)
    oct_shift = degree // len(sc)
    return root_midi + sc[idx] + (octave + oct_shift) * 12

def chord_notes(root_midi: int, quality_name: str, octave: int = 0) -> List[int]:
    intervals = CHORD_QUALITIES.get(quality_name, CHORD_QUALITIES["min7"])
    return [root_midi + i + octave * 12 for i in intervals]

def progression_chord_root(prog_name: str, step: int, root_midi: int, scale_name: str) -> int:
    prog = PROGRESSIONS.get(prog_name, PROGRESSIONS["dreamy_1"])
    deg, _ = prog[step % len(prog)]
    return scale_degree_to_midi(deg, root_midi, scale_name)

def clamp(v, lo=0, hi=1.0):
    return max(lo, min(hi, v))

def lerp(a, b, t):
    return a + (b - a) * clamp(t)

def unipolar(v):
    return clamp(v * 0.5 + 0.5)

def db_to_gain(db: float) -> float:
    return 10 ** (db / 20)

def entropy(values: List[float]) -> float:
    s = sum(values)
    if s <= 0: return 0.0
    return -sum((v / s) * math.log2(v / s + 1e-12) for v in values if v > 0)

# ═══════════════════════════════════════════════════════════════════════════
# DATA → MUSIC MAPPING ENGINE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class RecoveryData:
    """Complete data snapshot mapped to musical parameters."""
    pct: float = 0.0
    rate: float = 0.0
    bad_sectors: int = 0
    bad_kb: int = 0
    rescued_gb: float = 0.0
    total_gb: float = 400.0
    eta_h: float = 24.0
    elapsed_s: float = 0.0
    dd_running: bool = False
    carving_pct: float = 0.0
    total_files: int = 0
    carving_running: bool = False
    jpg: int = 0; mp4: int = 0; png: int = 0; mov: int = 0
    gif: int = 0; avi: int = 0; wav: int = 0; pdf: int = 0
    zipf: int = 0; htm: int = 0; other: int = 0
    vitality: float = 0.0
    chaos: float = 0.0
    corruption: float = 0.0
    dreaminess: float = 0.5
    jpg_ratio: float = 0.0
    video_ratio: float = 0.0
    gif_ratio: float = 0.0
    type_entropy: float = 0.0
    type_rarity: float = 0.0
    harmonic_tension: float = 0.0
    data_flux: float = 0.0
    recovery_momentum: float = 0.0
    efficiency: float = 0.0
    peak_ratio: float = 1.0
    rate_history: deque = field(default_factory=lambda: deque(maxlen=60))
    bad_history: deque = field(default_factory=lambda: deque(maxlen=60))
    file_history: deque = field(default_factory=lambda: deque(maxlen=60))

    def compute_derived(self, prev: Optional['RecoveryData'] = None):
        total_gb = max(self.total_gb, 0.01)
        self.vitality = clamp(self.rate / 20.0)
        self.corruption = self.bad_kb / max(self.rescued_gb * 1024, 1)
        self.chaos = (
            math.log1p(self.bad_sectors) / math.log1p(500) * 0.4 +
            (1 - self.vitality) * 0.3 +
            clamp(self.corruption * 6) * 0.3
        )
        self.harmonic_tension = self.chaos * 0.6 + self.corruption * 0.4
        self.dreaminess = max(0.05, 1.0 - self.harmonic_tension)
        total_fm = max(self.total_files, 1)
        self.jpg_ratio = self.jpg / total_fm
        self.video_ratio = (self.mp4 + self.mov) / total_fm
        self.gif_ratio = self.gif / total_fm
        all_types = [self.jpg, self.mp4, self.png, self.mov, self.gif,
                     self.avi, self.wav, self.pdf, self.zipf, self.htm, self.other]
        self.type_entropy = entropy(all_types) / 3.46
        rare_types = self.gif + self.wav + self.pdf + self.zipf + self.avi + self.htm
        self.type_rarity = clamp(rare_types / total_fm * 5)
        self.data_flux = clamp(
            self.vitality * 0.4 + abs(self.recovery_momentum) * 0.3 +
            min(self.total_files - (prev.total_files if prev else 0), 500) / 500 * 0.3
        )
        if self.elapsed_s > 0:
            self.efficiency = self.rescued_gb / (self.elapsed_s / 3600)
        if self.rate_history:
            peak = max(self.rate_history)
            self.peak_ratio = self.rate / max(peak, 0.01)
        self.rate_history.append(self.rate)
        self.bad_history.append(self.bad_sectors)
        self.file_history.append(self.total_files)
        return self


class MusicalMapper:
    """Translates RecoveryData into all musical parameters."""

    def __init__(self, data: RecoveryData, bpm_override: Optional[int] = None):
        self.d = data
        self.seed_base = int(data.pct * 1000 + data.rate * 100 + data.bad_sectors)
        self.random_generator = random.Random(self.seed_base)  # created early for selection randomization
        self.bpm = bpm_override or int(65 + data.rate * 2.5 + (100 - min(data.eta_h, 72)) * 0.15)
        self.bpm = clamp(self.bpm, 60, 100)
        vaporwave_keys = [48, 50, 51, 53, 55, 56, 58, 60, 57, 55, 53, 50, 48]
        arc_idx = int(data.pct / 100 * (len(vaporwave_keys) - 1))
        self.root_midi = vaporwave_keys[arc_idx]
        if data.chaos > 0.6:
            self.root_midi += random.randint(-1, 1)
        self.root_midi = clamp(self.root_midi, 40, 72)
        # Scale selection with randomization
        chaos = data.chaos
        te = data.type_entropy
        scale_pool = ["minor_penta"]
        if chaos < 0.15:               scale_pool = ["major_penta", "minor_penta", "dorian"]
        elif chaos < 0.25:             scale_pool = ["minor_penta", "dorian", "blues"]
        elif chaos < 0.35:             scale_pool = ["dorian", "blues", "natural_minor"]
        elif chaos < 0.45:             scale_pool = ["blues", "phrygian", "japanese"]
        elif chaos < 0.55:             scale_pool = ["japanese", "phrygian", "harmonic_minor"] if te > 0.5 else ["phrygian", "blues", "mixolydian"]
        elif chaos < 0.65:             scale_pool = ["harmonic_minor", "phrygian", "melodic_minor"]
        elif chaos < 0.78:             scale_pool = ["egyptian", "hirajoshi", "diminished"]
        elif chaos < 0.88:             scale_pool = ["hirajoshi", "diminished", "locrian"]
        else:                          scale_pool = ["diminished", "whole_tone", "locrian"]
        if data.corruption > 0.5:      scale_pool = ["locrian", "phrygian", "diminished"] if chaos > 0.5 else ["phrygian", "harmonic_minor", "blues"]
        idx_s = int(self.random_generator.random() ** 1.3 * len(scale_pool))
        self.scale = scale_pool[min(idx_s, len(scale_pool) - 1)]
        # Chord quality with randomization
        chord_pool = ["min7"]
        if data.jpg_ratio > 0.55:           chord_pool = ["dreams", "maj9", "maj13"]
        elif data.jpg_ratio > 0.45:         chord_pool = ["maj9", "maj7", "add9", "dreams"]
        elif data.video_ratio > 0.45:       chord_pool = ["min11", "min9", "dom9"]
        elif data.gif_ratio > 0.12:         chord_pool = ["sus4", "sus2", "add9"]
        elif data.corruption > 0.35:        chord_pool = ["m7b5", "dim7", "aug7"]
        elif data.type_rarity > 0.4:        chord_pool = ["quartal", "cluster", "dom7"]
        elif chaos > 0.75:                  chord_pool = ["dim7", "m7b5", "aug7"]
        elif data.dreaminess > 0.7:         chord_pool = ["mallsoft", "dreams", "min11"]
        else:                               chord_pool = ["min7", "min9", "sus4"]
        idx_c = int(self.random_generator.random() ** 1.5 * len(chord_pool))
        self.chord_quality = chord_pool[min(idx_c, len(chord_pool) - 1)]
        # Choose progression pool from data, then randomly select
        prog_pool = ["dreamy_1", "dreamy_2"]
        if data.jpg_ratio > 0.6:
            prog_pool = ["nostalgia", "eccojams", "crystal_dawn"]
        elif data.video_ratio > 0.5:
            prog_pool = ["late_nite", "future_funk", "vapor_drip"]
        elif data.gif_ratio > 0.08:
            prog_pool = ["eccojams", "plaza", "hex_sunset"]
        elif chaos > 0.7:
            prog_pool = ["corruption", "broken_drive", "mallsoft"]
        elif chaos > 0.55:
            prog_pool = ["broken_drive", "808_beat", "mallsoft"]
        elif data.dreaminess > 0.75:
            prog_pool = ["crystal_dawn", "eternal_dusk", "liminal", "hex_sunset"]
        elif data.vitality > 0.75:
            prog_pool = ["future_funk", "808_beat", "vapor_drip", "plaza"]
        elif data.type_rarity > 0.3:
            prog_pool = ["hex_sunset", "liminal", "eternal_dusk"]
        elif data.vitality > 0.5:
            prog_pool = ["vapor_drip", "late_nite", "future_funk"]
        elif data.dreaminess > 0.55:
            prog_pool = ["eternal_dusk", "crystal_dawn", "nostalgia"]
        # Random selection from pool for variety (weighted toward first)
        idx = int(self.random_generator.random() ** 1.5 * len(prog_pool))
        self.prog_name = prog_pool[min(idx, len(prog_pool) - 1)]
        self.progression = PROGRESSIONS[self.prog_name]
        self.lpf_cutoff_ratio = 0.1 + data.pct / 100 * 0.85
        self.lpf_resonance = 0.05 + chaos * 0.55
        self.reverb_mix = 0.25 + data.dreaminess * 0.55
        self.reverb_decay = 0.35 + data.dreaminess * 0.5 + data.type_rarity * 0.15
        self.delay_mix = 0.08 + data.dreaminess * 0.25
        self.tape_wow_depth = data.chaos * 0.004 + data.corruption * 0.003
        self.tape_saturation = 0.25 + data.chaos * 0.45
        self.sidechain_depth = 0.15 + data.vitality * 0.55
        self.bitcrush_amount = data.chaos * 0.3 + data.corruption * 0.2
        self.chorus_depth = 0.002 + data.dreaminess * 0.005
        self.chorus_rate = 0.1 + data.type_entropy * 0.25
        self.kick_gain = 0.85 + data.vitality * 0.12
        self.snare_gain = 0.6 + data.chaos * 0.15
        self.hat_gain = 0.2 + data.bad_sectors / 500 * 0.12
        self.fill_probability = data.chaos * 0.45 + data.corruption * 0.25
        self.ghost_note_probability = data.bad_sectors / 200 * 0.5
        self.open_hat_probability = 0.1 + data.vitality * 0.4
        self.bass_gain = 0.45 + data.chaos * 0.15
        self.bass_lpf = 200 + data.vitality * 600
        if data.vitality > 0.7:       self.bass_pattern = "funky"
        elif data.chaos > 0.6:        self.bass_pattern = "syncopated"
        elif data.vitality > 0.4:     self.bass_pattern = "walking"
        elif data.chaos > 0.3:        self.bass_pattern = "offbeat"
        else:                         self.bass_pattern = "simple"
        self.pad_voices = 2 + int(data.dreaminess * 4)
        self.pad_detune = 0.015 + data.chaos * 0.045
        self.pad_attack = 0.2 + data.dreaminess * 0.6
        self.pad_release = 1.2 + data.dreaminess * 1.8
        self.pad_gain = 0.18 + data.dreaminess * 0.1
        self.fm_probability = 0.1 + data.jpg_ratio * 0.5 + data.gif_ratio * 0.3
        self.fm_mod_index = 1.5 + data.jpg_ratio * 5 + data.gif_ratio * 3
        self.fm_gain = 0.12 + data.gif_ratio * 0.25
        self.bell_count = max(1, int(data.jpg / max(data.total_files, 1) * 16 + 3))
        self.arp_active = data.vitality > 0.25
        self.arp_rate_div = max(1, int(8 - data.vitality * 7))
        self.arp_octave_jump = data.vitality > 0.6
        self.arp_gain = 0.08 + data.vitality * 0.18
        self.detect_sections()

    def detect_sections(self):
        d = self.d
        pct = d.pct / 100
        if pct < 0.15:
            self.sections = [(0, "intro", 0.3, "scan beginning"), (0.4, "verse", 0.5, "first extraction")]
        elif pct < 0.35:
            self.sections = [(0, "intro", 0.4, "ramping up"), (0.25, "verse", 0.6, "data flowing"), (0.55, "chorus", 0.75, "peak extraction rate")]
        elif pct < 0.6:
            self.sections = [(0, "verse", 0.55, "steady recovery"), (0.3, "chorus", 0.8, "high throughput"), (0.55, "bridge", 0.5, "bad sector cluster"), (0.75, "chorus", 0.85, "resuming")]
        elif pct < 0.85:
            self.sections = [(0, "chorus", 0.7, "bulk extraction"), (0.35, "bridge", 0.45, "slowing sectors"), (0.55, "verse", 0.6, "carving files"), (0.75, "chorus", 0.9, "final surge")]
        else:
            self.sections = [(0, "bridge", 0.3, "last sectors"), (0.3, "outro", 0.5, "wrapping up"), (0.6, "outro", 0.2, "fading out")]
        if d.vitality > 0.7:
            for i in range(len(self.sections)):
                s, n, intens, desc = self.sections[i]
                self.sections[i] = (s, n, min(1.0, intens + 0.15), desc)

    def get_section_intensity(self, position_frac: float) -> float:
        if not self.sections:
            return 0.5
        for i in range(len(self.sections) - 1):
            pos_a, _, ia, _ = self.sections[i]
            pos_b, _, ib, _ = self.sections[i + 1]
            if pos_a <= position_frac <= pos_b:
                t = (position_frac - pos_a) / max(pos_b - pos_a, 0.001)
                return lerp(ia, ib, t)
        return self.sections[-1][2]

    def random(self) -> random.Random:
        return self.random_generator

    def should_trigger(self, probability: float) -> bool:
        return self.random_generator.random() < probability

    def describe(self) -> str:
        return (
            f"☉ {self.bpm}BPM | {note_name(self.root_midi)} {self.scale} | {self.chord_quality} | {self.prog_name}\n"
            f"   chaos:{self.d.chaos:.2f} dream:{self.d.dreaminess:.2f} vital:{self.d.vitality:.2f}\n"
            f"   reverb:{self.reverb_mix:.2f} LPF:{self.lpf_cutoff_ratio:.2f} SC:{self.sidechain_depth:.2f}\n"
            f"   fills:{self.fill_probability:.2f} ghosts:{self.ghost_note_probability:.2f} fm:{self.fm_probability:.2f}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# DSP UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def make_envelope(sr: int, duration: float, attack: float = 0.01,
                  decay: float = 0.1, sustain: float = 0.7,
                  release: float = 0.3) -> np.ndarray:
    n = int(sr * duration)
    na = int(sr * attack)
    nd = int(sr * decay)
    nr = int(sr * release)
    total_phases = na + nd + nr
    if total_phases > n and total_phases > 0:
        # Proportionally scale all phases to fit within n
        scale_factor = n / total_phases
        na = max(1, int(na * scale_factor))
        nd = max(1, int(nd * scale_factor))
        nr = max(1, int(nr * scale_factor))
        # Ensure they sum to exactly n
        na = min(na, n - nd - nr)
        nr = n - na - nd
    ns = max(0, n - na - nd - nr)
    env = np.full(n, sustain, dtype=np.float32)
    if na > 0 and na <= n:
        env[:na] = np.linspace(0, 1, na, dtype=np.float32) ** 0.6
    if nd > 0 and na + nd <= n:
        env_start = na
        env[env_start:env_start+nd] = np.linspace(1, sustain, nd, dtype=np.float32) ** 2.5
    if nr > 0 and nr <= n:
        env[-nr:] = np.linspace(sustain, 0, nr, dtype=np.float32) ** 3.0
    return env


def simple_lpf(signal: np.ndarray, cutoff_hz: float, sr: int = SAMPLE_RATE,
               resonance: float = 0.0) -> np.ndarray:
    if cutoff_hz >= 18000:
        return signal
    rc = 1.0 / (TAU * cutoff_hz)
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    out = np.zeros_like(signal)
    prev = 0.0
    fb_prev = 0.0
    for i in range(len(signal)):
        fb = signal[i] - resonance * (fb_prev - prev) * 0.5
        prev = prev + alpha * (fb - prev)
        fb_prev = prev
        out[i] = prev
    return np.clip(out, -2, 2)


def simple_hpf(signal: np.ndarray, cutoff_hz: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    if cutoff_hz <= 10:
        return signal
    rc = 1.0 / (TAU * cutoff_hz)
    dt = 1.0 / sr
    alpha = rc / (rc + dt)
    out = np.zeros_like(signal)
    prev_in = signal[0]
    prev_out = signal[0]
    for i in range(len(signal)):
        out[i] = alpha * (prev_out + signal[i] - prev_in)
        prev_out = out[i]
        prev_in = signal[i]
    return out


def soft_clip(x: np.ndarray, drive: float = 1.0) -> np.ndarray:
    return np.tanh(x * (1.0 + drive * 2.5)) * 0.9


def bitcrush(signal: np.ndarray, bits: int = 16, sr: int = SAMPLE_RATE,
             target_sr: int = SAMPLE_RATE) -> np.ndarray:
    if bits >= 16 and target_sr >= sr:
        return signal
    levels = 2 ** max(bits, 1)
    crushed = np.round(signal * levels) / (levels * 0.5)
    if target_sr < sr:
        ratio = sr / target_sr
        out = np.zeros_like(signal)
        held = crushed[0]
        for i in range(len(signal)):
            if i % max(1, int(ratio)) == 0:
                held = crushed[i]
            out[i] = held
        return out
    return crushed


def stereo_pan(mono: np.ndarray, pan: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    pan = clamp(pan, -1, 1)
    left_gain = math.cos((pan + 1) * PI / 4)
    right_gain = math.sin((pan + 1) * PI / 4)
    return mono * left_gain, mono * right_gain


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZER ENGINES
# ═══════════════════════════════════════════════════════════════════════════

class Oscillator:
    """Phase-accurate oscillator with FM, detune, and sync."""

    def __init__(self, sr: int = SAMPLE_RATE):
        self.sr = sr
        self.reset()

    def reset(self):
        self.phase = 0.0
        self.fm_phase = 0.0
        self.sync_phase = 0.0

    def sine(self, freq: float, duration: float) -> np.ndarray:
        n = int(self.sr * duration)
        t = np.arange(n) / self.sr
        phase = np.cumsum(np.full(n, freq / self.sr)) + self.phase
        self.phase = (phase[-1] + freq / self.sr) % 1.0
        return np.sin(TAU * phase)

    def saw(self, freq: float, duration: float) -> np.ndarray:
        n = int(self.sr * duration)
        phase = np.cumsum(np.full(n, freq / self.sr)) + self.phase
        self.phase = phase[-1] % 1.0
        return 2 * (phase % 1.0) - 1

    def triangle(self, freq: float, duration: float) -> np.ndarray:
        n = int(self.sr * duration)
        phase = np.cumsum(np.full(n, freq / self.sr)) + self.phase
        self.phase = phase[-1] % 1.0
        return 4 * np.abs(phase % 1.0 - 0.5) - 1

    def square(self, freq: float, duration: float, pw: float = 0.5) -> np.ndarray:
        n = int(self.sr * duration)
        phase = np.cumsum(np.full(n, freq / self.sr)) + self.phase
        self.phase = phase[-1] % 1.0
        return np.where((phase % 1.0) < pw, 1.0, -1.0)

    def noise(self, duration: float, color: str = 'white') -> np.ndarray:
        n = int(self.sr * duration)
        raw = np.random.randn(n).astype(np.float32)
        if color == 'pink':
            out = np.zeros(n, dtype=np.float32)
            b = [0.0] * 6
            for i in range(n):
                b[0] = 0.99886 * b[0] + raw[i] * 0.0555179
                b[1] = 0.99332 * b[1] + raw[i] * 0.0750759
                b[2] = 0.969 * b[2] + raw[i] * 0.153852
                b[3] = 0.8665 * b[3] + raw[i] * 0.3104856
                b[4] = 0.55 * b[4] + raw[i] * 0.5329522
                b[5] = -0.7616 * b[5] - raw[i] * 0.016898
                out[i] = (b[0] + b[1] + b[2] + b[3] + b[4] + b[5] + raw[i] * 0.5362) * 0.11
            return out
        return raw * 0.3

    def fm_sine(self, freq: float, duration: float, mod_freq: float = None,
                mod_index: float = 1.0, feedback: float = 0.0) -> np.ndarray:
        if mod_freq is None:
            mod_freq = freq * 3.0
        n = int(self.sr * duration)
        mod_phase = np.cumsum(np.full(n, mod_freq / self.sr)) + self.fm_phase
        self.fm_phase = mod_phase[-1] % 1.0
        mod = np.sin(TAU * mod_phase)
        car_phase = np.cumsum((freq + mod * mod_index * freq) / self.sr) + self.phase
        self.phase = car_phase[-1] % 1.0
        return np.sin(TAU * car_phase)

    def supersaw(self, freq: float, duration: float, voices: int = 7,
                 detune: float = 0.03) -> np.ndarray:
        n = int(self.sr * duration)
        mixed = np.zeros(n, dtype=np.float32)
        for v in range(voices):
            d = (v - voices // 2) * detune * freq
            voice = self.saw(freq + d, duration)
            self.reset()
            mixed += voice / voices * (0.85 if v == voices // 2 else 0.6)
        return mixed


# ═══════════════════════════════════════════════════════════════════════════
# DRUM SYNTHESIZER — Full 808 kit
# ═══════════════════════════════════════════════════════════════════════════

class DrumSynth:
    """Synthesizes classic 808 drum sounds."""
    def __init__(self, sr: int = SAMPLE_RATE):
        self.sr = sr
        self.osc = Oscillator(sr)

    def kick_808(self, pitch: float = 1.0, decay: float = 1.0, gain: float = 0.9,
                 click: float = 0.4, distortion: float = 0.0) -> np.ndarray:
        dur = 0.5
        n = int(self.sr * dur)
        t = np.arange(n) / self.sr
        f_start = 180 * pitch
        f_end = 45 * pitch
        freq = f_start * np.exp(-10 * decay * t)
        phase = TAU * np.cumsum(freq) / self.sr
        body = np.sin(phase)
        click_wave = np.sin(TAU * 900 * t) * np.exp(-70 * t) * click
        sub_phase = TAU * np.cumsum(np.full(n, f_end)) / self.sr
        sub_tail = np.sin(sub_phase) * np.exp(-8 * decay * t) * 0.15
        out = (body * 0.7 + click_wave + sub_tail) * np.exp(-4.5 * decay * t) * gain
        if distortion > 0:
            out = soft_clip(out * (1 + distortion * 2), drive=0.3 + distortion)
        return np.clip(out, -1, 1)

    def snare_808(self, pitch: float = 1.0, gain: float = 0.7,
                  snap: float = 0.5, gate_len: float = 0.14) -> np.ndarray:
        dur = 0.35
        n = int(self.sr * dur)
        t = np.arange(n) / self.sr
        tone1 = np.sin(TAU * 238 * pitch * t)
        tone2 = np.sin(TAU * 335 * pitch * t)
        tone_env = np.exp(-20 * t)
        tone = (tone1 * 0.5 + tone2 * 0.5) * tone_env * 0.35
        noise_raw = np.random.randn(n).astype(np.float32)
        noise_hp = np.zeros(n, dtype=np.float32)
        for i in range(1, n):
            noise_hp[i] = 0.998 * noise_hp[i-1] + noise_raw[i] - noise_raw[i-1]
        noise_env = np.exp(-22 * t)
        gate = np.ones(n)
        gate_start = int(self.sr * gate_len)
        if gate_start < n:
            gate[gate_start:] = np.exp(-35 * (t[gate_start:] - gate_len))
        out = (tone * 0.45 + noise_hp * 0.55 * snap) * noise_env * gate * gain
        return np.clip(out, -1, 1)

    def hihat(self, open_hat: bool = False, pitch: float = 1.0, gain: float = 0.35) -> np.ndarray:
        dur = 0.5 if open_hat else 0.12
        n = int(self.sr * dur)
        noise_raw = np.random.randn(n).astype(np.float32) * 0.5
        hp = np.zeros(n, dtype=np.float32)
        for i in range(1, n):
            hp[i] = 0.996 * hp[i-1] + noise_raw[i] - noise_raw[i-1]
        bp = np.zeros(n, dtype=np.float32)
        for i in range(2, n):
            bp[i] = 0.99 * bp[i-1] - 0.97 * bp[i-2] + hp[i] * 0.3
        env = np.exp(-30 * np.arange(n) / self.sr) if not open_hat else np.exp(-8 * np.arange(n) / self.sr)
        out = bp * env * gain * pitch
        return np.clip(out, -1, 1)

    def clap_808(self, gain: float = 0.4) -> np.ndarray:
        dur = 0.2
        n = int(self.sr * dur)
        t = np.arange(n) / self.sr
        out = np.zeros(n, dtype=np.float32)
        burst_times = [0.0, 0.02, 0.04, 0.06]
        for bt in burst_times:
            start = int(bt * self.sr)
            if start >= n: continue
            burst_len = n - start
            burst_noise = np.random.randn(burst_len).astype(np.float32) * 0.6
            burst_env = np.exp(-20 * np.arange(burst_len) / self.sr)
            out[start:] += burst_noise * burst_env * (0.65 if bt == 0 else 0.35)
        env = np.exp(-10 * t)
        return out * env * gain

    def rimshot(self, pitch: float = 1.0, gain: float = 0.3) -> np.ndarray:
        dur = 0.06
        n = int(self.sr * dur)
        t = np.arange(n) / self.sr
        tone = (np.sin(TAU * 1800 * pitch * t) * np.exp(-45 * t) * 0.5 +
                np.sin(TAU * 2400 * pitch * t) * np.exp(-50 * t) * 0.5)
        return tone * gain

    def tom(self, freq: float = 120, gain: float = 0.4) -> np.ndarray:
        dur = 0.3
        n = int(self.sr * dur)
        t = np.arange(n) / self.sr
        f_env = freq * np.exp(-6 * t)
        phase = TAU * np.cumsum(f_env) / self.sr
        body = np.sin(phase) * 0.6
        click = np.sin(TAU * freq * 2.5 * t) * np.exp(-25 * t) * 0.15
        env = np.exp(-7 * t)
        return (body + click) * env * gain

    def cymbal(self, gain: float = 0.25) -> np.ndarray:
        dur = 1.5
        n = int(self.sr * dur)
        noise_raw = np.random.randn(n).astype(np.float32)
        bp1 = np.zeros(n, dtype=np.float32)
        bp2 = np.zeros(n, dtype=np.float32)
        for i in range(2, n):
            bp1[i] = 0.995 * bp1[i-1] - 0.99 * bp1[i-2] + noise_raw[i] * 0.1
            bp2[i] = 0.998 * bp2[i-1] - 0.995 * bp2[i-2] + noise_raw[i] * 0.08
        env = np.exp(-3.5 * np.arange(n) / self.sr)
        return (bp1 * 0.6 + bp2 * 0.4) * env * gain


# ═══════════════════════════════════════════════════════════════════════════
# EFFECTS PROCESSORS
# ═══════════════════════════════════════════════════════════════════════════

class EffectsRack:
    """Rack of studio effects for vaporwave production."""

    def __init__(self, sr: int = SAMPLE_RATE):
        self.sr = sr

    def tape_wow_flutter(self, signal: np.ndarray, depth: float = 0.003,
                         rate: float = 0.4) -> np.ndarray:
        if depth <= 0:
            return signal
        n = len(signal)
        t = np.arange(n) / self.sr
        lfo1 = np.sin(TAU * rate * t) * 0.6
        lfo2 = np.sin(TAU * rate * 1.7 * t + 1.3) * 0.3
        lfo3 = np.sin(TAU * rate * 0.23 * t + 2.1) * 0.1
        modulation = (lfo1 + lfo2 + lfo3) * depth
        out = np.zeros_like(signal)
        read_pos = 0.0
        for i in range(n):
            idx = int(read_pos)
            frac = read_pos - idx
            if idx + 1 < n:
                out[i] = signal[idx] * (1 - frac) + signal[idx + 1] * frac
            elif idx < n:
                out[i] = signal[idx]
            read_pos += 1 + modulation[i] * 100
            read_pos = max(0, min(read_pos, n - 1.001))
        return out

    def reverb_schroeder(self, signal: np.ndarray, mix: float = 0.35,
                         decay: float = 0.5) -> np.ndarray:
        if mix <= 0:
            return signal
        n = len(signal)
        comb_delays = [1117, 1277, 1489, 1601, 1823, 1999]
        comb_gains = [0.70, 0.68, 0.65, 0.62, 0.58, 0.54]
        comb_gains = [g * decay for g in comb_gains]
        wet = np.zeros(n, dtype=np.float32)
        for delay, g in zip(comb_delays, comb_gains):
            buf = np.zeros(delay + n, dtype=np.float32)
            g_decay = g ** (1.0 / delay)
            for i in range(n):
                buf[delay + i] = signal[i] + g_decay * buf[i]
                wet[i] += buf[delay + i]
        wet /= len(comb_delays)
        for _ in range(2):
            ap_delay = 487 if _ == 0 else 269
            ap_gain = 0.55
            buf = np.zeros(ap_delay + n, dtype=np.float32)
            for i in range(n):
                delayed = buf[i]
                buf[ap_delay + i] = wet[i] + ap_gain * delayed
                wet[i] = delayed - ap_gain * buf[ap_delay + i]
        wet *= 0.55
        return signal * (1 - mix) + wet * mix

    def pingpong_delay(self, signal: np.ndarray, time_s: float = 0.25,
                       feedback: float = 0.4, mix: float = 0.25) -> Tuple[np.ndarray, np.ndarray]:
        if mix <= 0:
            return signal, signal
        n = len(signal)
        delay_samples = int(self.sr * time_s)
        left_out = np.zeros(n, dtype=np.float32)
        right_out = np.zeros(n, dtype=np.float32)
        left_buf = np.zeros(delay_samples + n, dtype=np.float32)
        right_buf = np.zeros(delay_samples + n, dtype=np.float32)
        for i in range(n):
            dry = signal[i]
            dl = left_buf[i]
            dr = right_buf[i]
            left_out[i] = dry + dl * mix
            right_out[i] = dry + dr * mix
            left_buf[delay_samples + i] = dry * 0.7 + dr * feedback * 0.7
            right_buf[delay_samples + i] = dry * 0.3 + dl * feedback * 0.7
        return left_out, right_out

    def chorus(self, signal: np.ndarray, rate: float = 0.2, depth: float = 0.003,
               mix: float = 0.5) -> np.ndarray:
        if mix <= 0:
            return signal
        n = len(signal)
        t = np.arange(n) / self.sr
        lfo_l = np.sin(TAU * rate * t) * depth * self.sr
        lfo_r = np.cos(TAU * rate * t) * depth * self.sr
        out = np.zeros_like(signal)
        for i in range(n):
            idx_l = int(i + lfo_l[i])
            frac_l = i + lfo_l[i] - idx_l
            idx_r = int(i + lfo_r[i])
            frac_r = i + lfo_r[i] - idx_r
            dl = 0.0; dr = 0.0
            if 0 <= idx_l + 1 < n:
                dl = signal[idx_l] * (1 - frac_l) + signal[idx_l + 1] * frac_l
            if 0 <= idx_r + 1 < n:
                dr = signal[idx_r] * (1 - frac_r) + signal[idx_r + 1] * frac_r
            out[i] = signal[i] * (1 - mix) + (dl + dr) * 0.5 * mix
        return out

    def sidechain_compressor(self, signal: np.ndarray, trigger: np.ndarray,
                             ratio: float = 3.0, attack: float = 0.003,
                             release: float = 0.08) -> np.ndarray:
        n = len(signal)
        at_coeff = math.exp(-1 / (attack * self.sr))
        rl_coeff = math.exp(-1 / (release * self.sr))
        envelope = np.zeros(n, dtype=np.float32)
        env = 0.0
        for i in range(n):
            t_val = abs(trigger[i]) if i < len(trigger) else 0
            env = max(t_val, env * (at_coeff if t_val > env else rl_coeff))
            envelope[i] = env
        smooth_env = np.zeros_like(envelope)
        alpha = 0.05
        smooth_env[0] = envelope[0]
        for i in range(1, n):
            smooth_env[i] = smooth_env[i-1] + alpha * (envelope[i] - smooth_env[i-1])
        gain = np.ones(n, dtype=np.float32)
        for i in range(n):
            db = 20 * math.log10(max(smooth_env[i], 1e-6))
            reduction_db = max(-36, db * (1 - 1/ratio))
            gain[i] = 10 ** (reduction_db / 20)
        gain_smooth = np.ones_like(gain)
        alpha_g = 0.1
        gain_smooth[0] = gain[0]
        for i in range(1, n):
            gain_smooth[i] = gain_smooth[i-1] + alpha_g * (gain[i] - gain_smooth[i-1])
        return signal * gain_smooth

    def multiband_compressor(self, signal: np.ndarray,
                             bands: List[Tuple[float, float, float, float]] = None) -> np.ndarray:
        if bands is None:
            bands = [(120, 1.5, 0.01, 0.1), (3000, 2.0, 0.005, 0.06), (18000, 3.0, 0.001, 0.03)]
        n = len(signal)
        out = np.zeros_like(signal)
        prev_lp = 0.0
        cutoff = bands[0][0]
        alpha = 1.0 / (1.0 + self.sr / (TAU * cutoff))
        cross_low = np.zeros(n, dtype=np.float32)
        for i in range(n):
            prev_lp = prev_lp + alpha * (signal[i] - prev_lp)
            cross_low[i] = prev_lp
        cross_mid_high = signal - cross_low
        for band_idx, (freq, ratio, att, rel) in enumerate(bands):
            if band_idx == 0:
                band_signal = cross_low
            else:
                band_signal = cross_mid_high
            rms_window = int(self.sr * 0.01)
            rms = np.zeros(n, dtype=np.float32)
            rms_acc = 0.0
            for i in range(n):
                rms_acc += band_signal[i]**2
                if i >= rms_window:
                    rms_acc -= band_signal[i - rms_window]**2
                rms[i] = math.sqrt(max(rms_acc / rms_window, 1e-12))
            env = 0.0
            gain = np.ones(n, dtype=np.float32)
            for i in range(n):
                env = max(rms[i], env * (0.1 if rms[i] > env else 0.01))
                db = 20 * math.log10(max(env, 1e-6))
                target_db = -12
                if db > target_db:
                    reduction = (db - target_db) * (1 - 1/ratio)
                    gain[i] = 10 ** (-reduction / 20)
            out += band_signal * gain * 0.8
        return out

    def lookahead_limiter(self, signal: np.ndarray, threshold: float = 0.95,
                          lookahead_ms: float = 3.0) -> np.ndarray:
        lookahead = int(self.sr * lookahead_ms / 1000)
        n = len(signal)
        out = np.zeros_like(signal)
        gain = np.ones(n, dtype=np.float32)
        envelope = np.abs(signal)
        smooth_env = np.zeros_like(envelope)
        smooth_env[0] = envelope[0]
        for i in range(1, n):
            smooth_env[i] = smooth_env[i-1] + 0.1 * (envelope[i] - smooth_env[i-1])
        for i in range(n):
            future_max = np.max(smooth_env[i:min(i + lookahead, n)]) if i < n - 1 else envelope[i]
            if future_max > threshold:
                gain[i] = threshold / future_max
            out[i] = signal[i] * gain[i]
        gain_sm = np.ones_like(gain)
        gain_sm[0] = gain[0]
        for i in range(1, n):
            gain_sm[i] = gain_sm[i-1] + 0.3 * (gain[i] - gain_sm[i-1])
        return signal * gain_sm


# ═══════════════════════════════════════════════════════════════════════════
# ARRANGER — Generative composition engine
# ═══════════════════════════════════════════════════════════════════════════

class VaporwaveArranger:
    """Generates complete vaporwave tracks from recovery data."""

    def __init__(self, data: RecoveryData, bpm: Optional[int] = None,
                 length_sec: float = 90.0):
        self.data = data
        self.map = MusicalMapper(data, bpm_override=bpm)
        self.sr = SAMPLE_RATE
        self.synth = Oscillator(self.sr)
        self.drums = DrumSynth(self.sr)
        self.fx = EffectsRack(self.sr)
        self.length_samples = int(self.sr * length_sec)
        self.length_sec = length_sec
        self.rand = self.map.random()

    def beats_to_samples(self, beats: float) -> int:
        return int(beats * 60.0 / self.map.bpm * self.sr)

    def render_to_stereo(self) -> Tuple[np.ndarray, np.ndarray]:
        n = self.length_samples
        left = np.zeros(n, dtype=np.float32)
        right = np.zeros(n, dtype=np.float32)
        sc_trigger = np.zeros(n, dtype=np.float32)

        beat_dur = 60.0 / self.map.bpm
        bar_dur = beat_dur * 4
        total_beats = int(self.length_sec / beat_dur)
        total_bars = total_beats // 4

        print(f"\n{'='*70}")
        print(self.map.describe())
        print(f"{'='*70}")
        print(f"  Sections: {[(s[1], f'{s[2]:.2f}') for s in self.map.sections]}")
        print(f"  Bass: {self.map.bass_pattern} | Arp: {self.map.arp_active}")
        print(f"  Pad voices: {self.map.pad_voices} | FM bells: {self.map.bell_count}")
        print(f"  Fill prob: {self.map.fill_probability:.2f} | Ghost prob: {self.map.ghost_note_probability:.2f}")
        print()

        # ──── PASS 1: Chord Pads ────
        print("  [1/7] Rendering pads...")
        pad_change_every_bars = 2
        for bar in range(0, total_bars, pad_change_every_bars):
            pos_frac = (bar * bar_dur) / self.length_sec
            intensity = self.map.get_section_intensity(pos_frac)
            step = bar // pad_change_every_bars
            deg, quality = self.map.progression[step % len(self.map.progression)]
            root = scale_degree_to_midi(deg, self.map.root_midi, self.map.scale)
            chord_q = quality if self.rand.random() > 0.2 else self.map.chord_quality
            notes = chord_notes(root, chord_q, octave=0)
            start_sample = int(bar * bar_dur * self.sr)
            dur_sec = min(bar_dur * pad_change_every_bars * 1.1, (n - start_sample) / self.sr)
            if dur_sec < 0.1:
                continue
            pad_wave = np.zeros(int(dur_sec * self.sr), dtype=np.float32)
            for note in notes:
                freq = midi_to_freq(note)
                for v in range(self.map.pad_voices):
                    detune_cents = (v - self.map.pad_voices // 2) * self.map.pad_detune * 100
                    detune_factor = 2 ** (detune_cents / 1200)
                    voice_freq = freq * detune_factor
                    if v % 2 == 0:
                        voice = self.synth.saw(voice_freq, dur_sec) * 0.5
                    else:
                        voice = self.synth.triangle(voice_freq, dur_sec) * 0.4
                    if v == self.map.pad_voices - 1:
                        voice += self.synth.fm_sine(voice_freq * 1.001, dur_sec,
                                                     mod_freq=voice_freq * 2,
                                                     mod_index=0.3) * 0.15
                    pad_wave += voice / (len(notes) * self.map.pad_voices) * self.map.pad_gain
            lpf_freq = 400 + self.map.lpf_cutoff_ratio * 12000 + intensity * 2000
            pad_wave = simple_lpf(pad_wave, lpf_freq, resonance=self.map.lpf_resonance * 0.5)
            env = make_envelope(self.sr, dur_sec, attack=self.map.pad_attack,
                               release=self.map.pad_release, sustain=0.6 + intensity * 0.2)
            if len(env) == len(pad_wave):
                pad_wave *= env
            pan = math.sin(TAU * bar / total_bars * 0.5) * 0.3
            l_pad, r_pad = stereo_pan(pad_wave, pan)
            end = min(start_sample + len(l_pad), n)
            left[start_sample:end] += l_pad[:end-start_sample]
            right[start_sample:end] += r_pad[:end-start_sample]

        # ──── PASS 2: Bassline ────
        print("  [2/7] Rendering bassline...")
        bass_pattern = BASS_PATTERNS[self.map.bass_pattern]
        bass_notes_pool = []
        for bar in range(0, total_bars, 2):
            step = bar // 2
            deg, quality = self.map.progression[step % len(self.map.progression)]
            root = scale_degree_to_midi(deg, self.map.root_midi, self.map.scale)
            sc = SCALES[self.map.scale]
            for o in [-1, 0]:
                for s in range(len(sc)):
                    bn = root + sc[s] + o * 12 - 12
                    if 28 <= bn <= 55:
                        bass_notes_pool.append(bn)
        if not bass_notes_pool:
            bass_notes_pool = [self.map.root_midi - 24, self.map.root_midi - 19,
                               self.map.root_midi - 17, self.map.root_midi - 12]
        prev_bass_note = bass_notes_pool[0]

        for bar in range(total_bars):
            pos_frac = (bar * bar_dur) / self.length_sec
            intensity = self.map.get_section_intensity(pos_frac)
            step = bar // 2
            deg, _ = self.map.progression[step % len(self.map.progression)]
            root = scale_degree_to_midi(deg, self.map.root_midi, self.map.scale)
            for sub in range(16):
                beat_idx = bar * 16 + sub
                if bass_pattern[sub % len(bass_pattern)]:
                    chord_tones = chord_notes(root, self.map.chord_quality, octave=-1)
                    chord_tones = [c for c in chord_tones if 28 <= c <= 55]
                    if self.rand.random() < 0.7 and chord_tones:
                        bass_note = self.rand.choice(chord_tones)
                    elif bass_notes_pool:
                        bass_note = self.rand.choice(bass_notes_pool)
                    else:
                        bass_note = root - 24
                    if self.rand.random() < 0.2 and prev_bass_note != bass_note:
                        bass_note = prev_bass_note + (1 if bass_note > prev_bass_note else -1)
                    prev_bass_note = bass_note
                    start_samp = int(beat_idx * beat_dur / 4 * self.sr)
                    dur = min(beat_dur / 4 * 0.85, (n - start_samp) / self.sr)
                    if dur < 0.01:
                        continue
                    freq = midi_to_freq(bass_note)
                    bass_wave = self.synth.fm_sine(freq, dur, mod_freq=freq * 2.0,
                                                    mod_index=1.5 + intensity * 1.5, feedback=0.1)
                    sub_wave = self.synth.sine(freq * 0.5, dur) * 0.3
                    bass_wave = bass_wave * 0.7 + sub_wave
                    env = make_envelope(self.sr, dur, attack=0.003, decay=0.04,
                                       sustain=0.55, release=0.08)
                    if len(env) == len(bass_wave):
                        bass_wave *= env
                    bass_lpf = self.map.bass_lpf + intensity * 300
                    bass_wave = simple_lpf(bass_wave, bass_lpf, resonance=0.5)
                    bass_wave *= self.map.bass_gain * (0.7 + intensity * 0.3)
                    end = min(start_samp + len(bass_wave), n)
                    left[start_samp:end] += bass_wave[:end-start_samp] * 0.7
                    right[start_samp:end] += bass_wave[:end-start_samp] * 0.7

        # ──── PASS 3: Drums ────
        print("  [3/7] Rendering drums...")
        kick = self.drums.kick_808(gain=self.map.kick_gain, decay=0.9 + self.data.vitality * 0.1,
                                    distortion=self.data.chaos * 0.4)
        snare = self.drums.snare_808(gain=self.map.snare_gain, snap=0.4 + self.data.chaos * 0.3)
        hat_c = self.drums.hihat(open_hat=False, gain=self.map.hat_gain)
        hat_o = self.drums.hihat(open_hat=True, gain=self.map.hat_gain * 1.3)
        clap = self.drums.clap_808(gain=0.35 + self.data.vitality * 0.1)
        rim = self.drums.rimshot(gain=0.25 + self.data.chaos * 0.1)
        tom_hi = self.drums.tom(freq=160, gain=0.35)
        tom_lo = self.drums.tom(freq=100, gain=0.4)
        cymbal = self.drums.cymbal(gain=0.2)

        fill_active = False
        fill_beats_remaining = 0
        for bar in range(total_bars):
            pos_frac = (bar * bar_dur) / self.length_sec
            intensity = self.map.get_section_intensity(pos_frac)
            if bar % 8 == 0:
                fill_prob = self.map.fill_probability * (1 + self.data.corruption * 2)
                if self.rand.random() < fill_prob:
                    fill_active = True
                    fill_beats_remaining = 8
            if fill_beats_remaining > 0:
                fill_beats_remaining -= 4
            else:
                fill_active = False

            for beat in range(4):
                beat_idx = bar * 4 + beat
                start_samp = int(beat_idx * beat_dur * self.sr)

                # KICK — intensity-responsive gain
                kick_section_gain = 0.7 + intensity * 0.3
                if beat in (0, 2):
                    sc_trigger[start_samp:start_samp+len(kick)] = kick
                    left[start_samp:min(start_samp+len(kick), n)] += kick[:min(len(kick), n-start_samp)] * kick_section_gain
                    right[start_samp:min(start_samp+len(kick), n)] += kick[:min(len(kick), n-start_samp)] * kick_section_gain
                if self.data.vitality > 0.55 and beat == 3 and self.rand.random() < 0.4:
                    ek_start = start_samp
                    sc_trigger[ek_start:ek_start+len(kick)] = kick * 0.6
                    left[ek_start:min(ek_start+len(kick), n)] += kick[:min(len(kick), n-ek_start)] * 0.4
                    right[ek_start:min(ek_start+len(kick), n)] += kick[:min(len(kick), n-ek_start)] * 0.4
                if fill_active and self.rand.random() < 0.6:
                    for sixteenth in range(4):
                        fk_start = start_samp + int(sixteenth * beat_dur / 4 * self.sr)
                        if fk_start < n:
                            sc_trigger[fk_start:fk_start+len(kick)] = kick * 0.5
                            left[fk_start:min(fk_start+len(kick), n)] += kick[:min(len(kick), n-fk_start)] * 0.3
                            right[fk_start:min(fk_start+len(kick), n)] += kick[:min(len(kick), n-fk_start)] * 0.3

                # SNARE
                if beat in (1, 3):
                    sn_gain = 0.55 + intensity * 0.2
                    left[start_samp:min(start_samp+len(snare), n)] += snare[:min(len(snare), n-start_samp)] * sn_gain
                    right[start_samp:min(start_samp+len(snare), n)] += snare[:min(len(snare), n-start_samp)] * sn_gain
                if self.rand.random() < self.map.ghost_note_probability:
                    ghost_sixteenths = self.rand.choice([1, 2, 3]) if beat not in (1, 3) else 0
                    for gs in range(4):
                        if gs != ghost_sixteenths or beat in (1, 3):
                            continue
                        gs_start = start_samp + int(gs * beat_dur / 4 * self.sr)
                        if gs_start < n:
                            left[gs_start:min(gs_start+len(snare), n)] += snare[:min(len(snare), n-gs_start)] * 0.12
                            right[gs_start:min(gs_start+len(snare), n)] += snare[:min(len(snare), n-gs_start)] * 0.1

                # HI-HAT — variable patterns with 16th note probability
                # Pattern changes based on bar position and data
                if bar % 8 < 4:
                    hat_pattern = [True, True, True, True] if self.data.vitality > 0.5 else \
                                  [True, False, True, False] if beat % 2 == 0 else [True, True, False, True]
                else:
                    hat_pattern = [True, False, True, True] if self.data.vitality > 0.4 else \
                                  [True, True, False, True]
                for hb in range(4):
                    # Random 16th note hat probability
                    hat_decide = hat_pattern[hb % 4] or self.rand.random() < (0.12 + self.data.chaos * 0.25)
                    if hat_decide:
                        h_start = start_samp + int(hb * beat_dur / 4 * self.sr)
                        h_sound = hat_o if (beat == 3 and hb == 3 and self.rand.random() < self.map.open_hat_probability) else hat_c
                        if h_start < n:
                            hat_pan = -0.3 + (hb % 4) * 0.2
                            l_h, r_h = stereo_pan(h_sound, hat_pan)
                            left[h_start:min(h_start+len(l_h), n)] += l_h[:min(len(l_h), n-h_start)] * 0.7
                            right[h_start:min(h_start+len(r_h), n)] += r_h[:min(len(r_h), n-h_start)] * 0.7

                # CLAP
                if beat == 2 and bar % 4 == 0:
                    left[start_samp:min(start_samp+len(clap), n)] += clap[:min(len(clap), n-start_samp)] * 0.75
                    right[start_samp:min(start_samp+len(clap), n)] += clap[:min(len(clap), n-start_samp)] * 0.75

                # RIMSHOT
                if self.data.gif_ratio > 0.06 and self.rand.random() < 0.25:
                    rim_hits = self.rand.choice([0, 2])
                    r_start = start_samp + int(rim_hits * beat_dur / 2 * self.sr)
                    if r_start < n:
                        left[r_start:min(r_start+len(rim), n)] += rim[:min(len(rim), n-r_start)] * 0.5
                        right[r_start:min(r_start+len(rim), n)] += rim[:min(len(rim), n-r_start)] * 0.45

                # TOM FILLS + SNARE ROLLS
                if fill_active and self.rand.random() < 0.5:
                    # 16th note tom fill
                    tom_seq = [tom_hi, tom_lo, tom_hi, tom_lo] if self.rand.random() > 0.5 else [tom_lo, tom_hi, tom_lo, tom_hi]
                    for ti, ts in enumerate(tom_seq):
                        t_start = start_samp + int(ti * beat_dur / 4 * self.sr)
                        if t_start < n:
                            pan_tom = -0.6 + ti * 0.4
                            l_t, r_t = stereo_pan(ts, pan_tom)
                            left[t_start:min(t_start+len(l_t), n)] += l_t[:min(len(l_t), n-t_start)]
                            right[t_start:min(t_start+len(r_t), n)] += r_t[:min(len(r_t), n-t_start)]
                # Snare roll build-up: 8th or 16th note snare flam
                if bar % 8 == 7 and beat == 3 and self.rand.random() < (0.3 + self.data.vitality * 0.4):
                    for roll_step in range(4):
                        roll_start = start_samp + int(roll_step * beat_dur / 8 * self.sr)
                        if roll_start < n:
                            roll_gain = 0.2 + roll_step * 0.1
                            left[roll_start:min(roll_start+len(snare), n)] += snare[:min(len(snare), n-roll_start)] * roll_gain
                            right[roll_start:min(roll_start+len(snare), n)] += snare[:min(len(snare), n-roll_start)] * roll_gain * 0.9

                # CYMBAL — every 8 or 16 bars, probability-driven
                if (bar % 16 == 0 or (bar % 8 == 0 and self.rand.random() < 0.3)) and beat == 0:
                    c_start = start_samp
                    if c_start < n:
                        left[c_start:min(c_start+len(cymbal), n)] += cymbal[:min(len(cymbal), n-c_start)] * 0.7
                        right[c_start:min(c_start+len(cymbal), n)] += cymbal[:min(len(cymbal), n-c_start)] * 0.6

        # ──── PASS 4: FM Bells ────
        print("  [4/7] Rendering FM textures...")
        bell_count = self.map.bell_count
        for i in range(bell_count):
            pos_frac = (i / bell_count) * 0.9
            if not self.map.should_trigger(self.map.fm_probability):
                continue
            step = (i * 3) % len(self.map.progression)
            deg, _ = self.map.progression[step]
            root = scale_degree_to_midi(deg, self.map.root_midi, self.map.scale)
            chord_t = chord_notes(root, self.map.chord_quality, octave=1)
            bell_note = chord_t[i % len(chord_t)]
            bell_pos = int(pos_frac * n)
            if bell_pos + 100 >= n:
                break
            dur = 0.8 + self.rand.random() * 2.0
            mod_idx = self.map.fm_mod_index * (0.7 + self.rand.random() * 0.6)
            bell = self.synth.fm_sine(midi_to_freq(bell_note), dur,
                                       mod_freq=midi_to_freq(bell_note) * (2.5 + self.rand.random() * 5),
                                       mod_index=mod_idx, feedback=self.rand.random() * 0.1)
            env = np.exp(-3.5 * np.arange(len(bell)) / self.sr)
            bell *= env * self.map.fm_gain
            pan = -0.6 + (i % 5) * 0.3 + self.rand.random() * 0.2
            l_b, r_b = stereo_pan(bell, pan)
            be_len = min(len(l_b), n - bell_pos)
            if be_len > 0:
                left[bell_pos:bell_pos+be_len] += l_b[:be_len]
                right[bell_pos:bell_pos+be_len] += r_b[:be_len]

        # ──── PASS 5: Arpeggio ────
        print("  [5/7] Rendering arpeggios...")
        if self.map.arp_active:
            sc = SCALES[self.map.scale]
            step_every = self.map.arp_rate_div
            for beat in range(0, total_beats, step_every):
                pos_frac = (beat * beat_dur) / self.length_sec
                intensity = self.map.get_section_intensity(pos_frac)
                octave_jump = 2 if (self.map.arp_octave_jump and (beat // step_every) % 3 == 0) else 1
                bar_idx = beat // 4
                step = bar_idx // 2
                deg, _ = self.map.progression[step % len(self.map.progression)]
                root = scale_degree_to_midi(deg, self.map.root_midi, self.map.scale)
                chord_t = chord_notes(root, self.map.chord_quality, octave=octave_jump)
                arp_note = chord_t[(beat // step_every) % len(chord_t)]
                start_samp = int(beat * beat_dur * self.sr)
                dur = min(beat_dur * 0.5, (n - start_samp) / self.sr)
                if dur < 0.02:
                    continue
                arp_wave = self.synth.fm_sine(midi_to_freq(arp_note), dur,
                                               mod_freq=midi_to_freq(arp_note) * (1.5 + self.rand.random() * 2),
                                               mod_index=1.0 + self.data.vitality * 2.5)
                env = make_envelope(self.sr, dur, attack=0.005, decay=0.03, sustain=0.3, release=0.08)
                if len(env) == len(arp_wave):
                    arp_wave *= env
                arp_wave *= self.map.arp_gain * (0.5 + intensity * 0.5)
                pan = -0.4 + (beat % 6) * 0.16
                l_a, r_a = stereo_pan(arp_wave, pan)
                a_len = min(len(l_a), n - start_samp)
                if a_len > 0:
                    left[start_samp:start_samp+a_len] += l_a[:a_len]
                    right[start_samp:start_samp+a_len] += r_a[:a_len]

        # ──── PASS 6: Ambient Textures ────
        print("  [6/7] Rendering ambient textures...")
        if self.data.chaos > 0.2:
            noise_level = 0.003 + self.data.chaos * 0.012
            vinyl = self.synth.noise(self.length_sec, color='pink') * noise_level
            vinyl = simple_hpf(vinyl, 200) * 0.6
            v_len = min(len(vinyl), n)
            left[:v_len] += vinyl[:v_len] * 0.5
            right[:v_len] += vinyl[:v_len] * 0.5
        drone_freq = midi_to_freq(self.map.root_midi - 24)
        drone = self.synth.sine(drone_freq, self.length_sec) * 0.08 * self.data.dreaminess
        d_len = min(len(drone), n)
        left[:d_len] += drone[:d_len] * 0.5
        right[:d_len] += drone[:d_len] * 0.5

        # ──── PASS 7: Mix Processing ────
        print("  [7/7] Processing mix...")
        if self.map.sidechain_depth > 0.15:
            sc_ratio = 2.0 + self.map.sidechain_depth * 8
            left = self.fx.sidechain_compressor(left, sc_trigger, ratio=sc_ratio)
            right = self.fx.sidechain_compressor(right, sc_trigger, ratio=sc_ratio)
        if self.map.chorus_depth > 0.001:
            left = self.fx.chorus(left, rate=self.map.chorus_rate, depth=self.map.chorus_depth, mix=0.3)
            right = self.fx.chorus(right, rate=self.map.chorus_rate * 1.07, depth=self.map.chorus_depth * 0.8, mix=0.3)
        if self.map.tape_wow_depth > 0.0005:
            left = self.fx.tape_wow_flutter(left, depth=self.map.tape_wow_depth, rate=0.35 + self.data.chaos * 0.3)
            right = self.fx.tape_wow_flutter(right, depth=self.map.tape_wow_depth, rate=0.38 + self.data.chaos * 0.3)
        if self.map.delay_mix > 0.05:
            delay_time = bar_dur * 0.75
            left, right = self.fx.pingpong_delay(left, time_s=delay_time,
                                                  feedback=0.3 + self.data.dreaminess * 0.25,
                                                  mix=self.map.delay_mix)
        if self.map.reverb_mix > 0.1:
            left = self.fx.reverb_schroeder(left, mix=self.map.reverb_mix, decay=self.map.reverb_decay)
            right = self.fx.reverb_schroeder(right, mix=self.map.reverb_mix, decay=self.map.reverb_decay)
        left = soft_clip(left, drive=self.map.tape_saturation)
        right = soft_clip(right, drive=self.map.tape_saturation)
        if self.map.bitcrush_amount > 0.05:
            bits = max(6, int(16 - self.map.bitcrush_amount * 12))
            target_sr = max(4000, int(SAMPLE_RATE * (1 - self.map.bitcrush_amount * 0.8)))
            left = bitcrush(left, bits=bits, target_sr=target_sr)
            right = bitcrush(right, bits=bits, target_sr=target_sr)
        # Mastering chain — controlled loudness with smooth tape effects
        # Stage 1: Gentle multiband glue (less aggressive)
        left_mb = self.fx.multiband_compressor(left)
        right_mb = self.fx.multiband_compressor(right)
        left = left * 0.4 + left_mb * 0.6
        right = right * 0.4 + right_mb * 0.6
        # Stage 2: Soft clip for warmth
        left = soft_clip(left, drive=self.map.tape_saturation * 0.8)
        right = soft_clip(right, drive=self.map.tape_saturation * 0.8)
        # Stage 3: Brickwall limiter
        left = self.fx.lookahead_limiter(left, threshold=0.85, lookahead_ms=2.5)
        right = self.fx.lookahead_limiter(right, threshold=0.85, lookahead_ms=2.5)
        # Stage 4: Final gain — loud and clean
        boost = 1.0 + self.data.vitality * 0.12
        left = np.clip(left * boost, -0.98, 0.98)
        right = np.clip(right * boost, -0.98, 0.98)

        # Tape slowdown & recovery (classic vaporwave — smooth, no hard cut)
        if self.data.chaos > 0.35:
            stop_pos = 0.55 + self.rand.random() * 0.25  # 55-80% through track
            stop_start = int(n * stop_pos)
            effect_dur = int(self.sr * (1.8 + self.rand.random() * 2.5))  # 1.8-4.3 seconds
            stop_end = min(stop_start + effect_dur, n - int(self.sr * 2))
            if stop_end > stop_start + 2000:
                effect_samples = stop_end - stop_start
                t_eff = np.arange(effect_samples) / self.sr
                eff_dur_s = effect_samples / self.sr
                # Speed envelope: normal → slow → normal (V-shaped recovery)
                # Creates a smooth pitch-drop-and-return
                mid_point = eff_dur_s * 0.45
                speed = np.ones(effect_samples, dtype=np.float32)
                for i in range(effect_samples):
                    ti = t_eff[i]
                    if ti < mid_point:
                        # Slowdown phase: 1.0 → 0.08
                        speed[i] = np.exp(-5.0 * ti / mid_point) * 0.92 + 0.08
                    else:
                        # Recovery phase: 0.08 → 1.0
                        recovery_t = (ti - mid_point) / (eff_dur_s - mid_point)
                        speed[i] = 0.08 + 0.92 * (1 - np.exp(-4.0 * recovery_t))
                # Volume envelope: slight dip during the slowdown
                vol_env = np.ones(effect_samples, dtype=np.float32)
                for i in range(effect_samples):
                    ti = t_eff[i]
                    if ti < mid_point * 0.7:
                        vol_env[i] = 1.0
                    elif ti < mid_point * 1.5:
                        # Dip to ~55% at the slowest point
                        dip_t = (ti - mid_point * 0.7) / (mid_point * 0.8)
                        vol_env[i] = 1.0 - 0.45 * np.sin(dip_t * PI / 2)
                    else:
                        # Recover
                        rec_t = (ti - mid_point * 1.5) / max(eff_dur_s - mid_point * 1.5, 0.01)
                        vol_env[i] = 0.55 + 0.45 * (1 - np.exp(-5.0 * rec_t))
                # Resample with speed envelope
                out_l = np.zeros(effect_samples, dtype=np.float32)
                out_r = np.zeros(effect_samples, dtype=np.float32)
                read_pos = 0.0
                for i in range(effect_samples):
                    idx = int(read_pos)
                    frac = read_pos - idx
                    src_idx = stop_start + idx
                    if src_idx + 1 < n:
                        out_l[i] = (left[src_idx] * (1 - frac) + left[src_idx + 1] * frac) * vol_env[i]
                        out_r[i] = (right[src_idx] * (1 - frac) + right[src_idx + 1] * frac) * vol_env[i]
                    elif src_idx < n:
                        out_l[i] = left[src_idx] * vol_env[i]
                        out_r[i] = right[src_idx] * vol_env[i]
                    read_pos += speed[i]
                # Blend: crossfade into the effected section and back out
                xfade_len = int(self.sr * 0.15)  # 150ms crossfade
                left[stop_start:stop_end] = out_l
                right[stop_start:stop_end] = out_r
                # Smooth entry crossfade
                if stop_start > xfade_len:
                    xf_in = np.linspace(0, 1, xfade_len, dtype=np.float32)
                    left[stop_start:stop_start+xfade_len] = (
                        left[stop_start:stop_start+xfade_len] * xf_in +
                        left[stop_start-xfade_len:stop_start][::-1] * (1 - xf_in)
                    )
                    right[stop_start:stop_start+xfade_len] = (
                        right[stop_start:stop_start+xfade_len] * xf_in +
                        right[stop_start-xfade_len:stop_start][::-1] * (1 - xf_in)
                    )

        fade_len = int(self.sr * 4.0)
        if fade_len < n:
            fade = 0.5 + 0.5 * np.cos(np.linspace(0, PI, fade_len, dtype=np.float32))
            left[-fade_len:] *= fade
            right[-fade_len:] *= fade

        peak = max(np.max(np.abs(left)), np.max(np.abs(right)))
        rms_l = np.sqrt(np.mean(left ** 2))
        rms_r = np.sqrt(np.mean(right ** 2))
        print(f"  Final — Peak: {peak:.4f}  RMS(L): {rms_l:.4f}  RMS(R): {rms_r:.4f}")
        return left, right


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING & SIMULATION
# ═══════════════════════════════════════════════════════════════════════════

def load_status(path: str) -> dict:
    with open(path) as f:
        return json.load(f)

def status_to_data(status: dict, prev_data: Optional[RecoveryData] = None) -> RecoveryData:
    dd = status.get("ddrescue") or {}
    fm = status.get("foremost") or {}
    byt = fm.get("by_type") or {}
    d = RecoveryData(
        pct=float(dd.get("pct", 0)),
        rate=float(dd.get("rate_gb_h", 0)),
        bad_sectors=int(dd.get("bad_sectors", 0)),
        bad_kb=int(dd.get("bad_kb", 0)),
        rescued_gb=float(dd.get("rescued_gb", 0)),
        total_gb=float(dd.get("total_gb", 400)),
        eta_h=float(dd.get("eta_h", 24)),
        elapsed_s=float(dd.get("elapsed_s", 0)),
        dd_running=bool(dd.get("running", False)),
        carving_pct=float(fm.get("pct", 0)),
        total_files=int(fm.get("total_files", 0)),
        carving_running=bool(fm.get("running", False)),
        jpg=int(byt.get("jpg", 0)), mp4=int(byt.get("mp4", 0)),
        png=int(byt.get("png", 0)), mov=int(byt.get("mov", 0)),
        gif=int(byt.get("gif", 0)), avi=int(byt.get("avi", 0)),
        wav=int(byt.get("wav", 0)), pdf=int(byt.get("pdf", 0)),
        zipf=int(byt.get("zip", 0)), htm=int(byt.get("htm", 0)),
        other=int(byt.get("other", 0)),
    )
    if prev_data and prev_data.pct > 0:
        d.recovery_momentum = clamp((d.pct - prev_data.pct) / max(prev_data.pct, 0.01), -1, 1)
    if prev_data:
        d.rate_history = prev_data.rate_history
        d.bad_history = prev_data.bad_history
        d.file_history = prev_data.file_history
    d.compute_derived(prev_data)
    return d


def sim_status(length_sec: float = 90.0, seed: int = None) -> dict:
    """Generate varied simulated status for demo purposes."""
    t = random.uniform(0, 400)
    # Vary the recovery profile dramatically by seed for musical variety
    profile = random.random()  # 0.0-1.0 recovery profile type
    pct = min(98, t / 4.5 + math.sin(t * 0.03) * 3 + random.uniform(1, 20))
    base_rate = 1 + random.uniform(0.5, 8) + math.sin(t * 0.15) * 2.0
    spike = random.uniform(2, 10) if random.random() < 0.08 else 0
    dip = -random.uniform(0.5, 3) if random.random() < 0.06 else 0
    rate = max(0, base_rate + spike + dip + math.sin(t * 0.9) * 0.6 +
               math.sin(t * 2.7) * 0.3 + math.sin(t * 5.1) * 0.15)
    base_bad = max(0, int(random.uniform(0, 30) + math.sin(t * 0.05) * 3 +
                   (random.randint(3, 15) if random.random() < 0.06 else 0) +
                   (random.randint(8, 30) if random.random() < 0.03 else 0)))
    bad_kb = base_bad * 4
    rescued_gb = round(pct * random.uniform(2, 5) + math.sin(t * 0.1) * 0.5, 2)
    total_gb = random.uniform(100, 500)
    fm_pct = min(98, pct * random.uniform(0.5, 0.9) + random.uniform(0, 15))
    # Vary file type distributions significantly
    jpg_bias = random.uniform(0.25, 0.65)
    mp4_bias = random.uniform(0.02, 0.20)
    gif_bias = random.uniform(0.01, 0.10)
    fm_files = max(0, int(pct * random.uniform(50, 500) + math.sin(t * 0.4) * 400 +
                   (random.randint(100, 1000) if random.random() < 0.08 else 0) +
                   (random.randint(50, 500) if random.random() < 0.04 else 0)))
    remaining = max(0, 100 - pct)
    eta_h = round(remaining / max(rate, 0.01), 1)
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ddrescue": {
            "pct": round(pct, 2), "rate_gb_h": round(rate, 3),
            "bad_sectors": base_bad, "bad_kb": bad_kb,
            "rescued_gb": rescued_gb, "total_gb": total_gb,
            "elapsed_s": int(t % 3600 * 100 + t * 3600 * 0.1),
            "eta_h": eta_h, "running": pct < 98,
        },
        "foremost": {
            "pct": round(fm_pct, 2), "total_files": fm_files,
            "total_size": f"{fm_files * 2.3:.1f} MB",
            "running": fm_pct < 85,
            "by_type": {
                "jpg": int(fm_files * (jpg_bias + math.sin(t * 0.08) * 0.15)),
                "mp4": int(fm_files * (mp4_bias + math.cos(t * 0.12) * 0.05)),
                "png": int(fm_files * (random.uniform(0.05, 0.20) + math.sin(t * 0.1) * 0.04)),
                "mov": int(fm_files * (random.uniform(0.02, 0.10) + math.cos(t * 0.15) * 0.03)),
                "gif": int(fm_files * (gif_bias + math.sin(t * 0.18) * 0.02)),
                "avi": int(fm_files * random.uniform(0.005, 0.04)),
                "wav": int(fm_files * random.uniform(0.005, 0.03)),
                "pdf": int(fm_files * random.uniform(0.003, 0.02)),
                "zip": int(fm_files * random.uniform(0.002, 0.01)),
                "htm": int(fm_files * random.uniform(0.003, 0.02)),
                "other": int(fm_files * random.uniform(0.02, 0.10)),
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(
        description="☉ Saint Charon — Vaporwave Synth Engine v4.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  python3 vaporwave_synth.py --sim --out dream.wav
  python3 vaporwave_synth.py --sim --length 180 --bpm 80 --seed 42
  python3 vaporwave_synth.py --status /tmp/status.json --out recovery.wav
        """)
    p.add_argument("--status", default=None, help="Path to status.json")
    p.add_argument("--sim", action="store_true", help="Use simulated data")
    p.add_argument("--out", default="vaporwave_recovery.wav", help="Output WAV file")
    p.add_argument("--bpm", type=int, default=None, help="BPM override")
    p.add_argument("--length", type=int, default=90, help="Track length in seconds")
    p.add_argument("--seed", type=int, default=None, help="RNG seed")
    args = p.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    if args.status:
        try:
            status = load_status(args.status)
            print(f"☉ Loaded status: {args.status}")
        except Exception as e:
            print(f"❌ Failed to load: {e}")
            sys.exit(1)
    elif args.sim:
        status = sim_status(args.length)
        print(f"☉ Generated simulated recovery data")
    else:
        print("❌ Use --sim or --status")
        sys.exit(1)

    data = status_to_data(status)

    dd = status.get("ddrescue", {})
    fm = status.get("foremost", {})

    print(f"\n{'='*60}")
    print(f"  ☉ SAINT CHARON — VAPORWAVE SYNTH ENGINE v4.0")
    print(f"  {'='*50}")
    print(f"  Recovery: {data.pct:.1f}% @ {data.rate:.2f} GB/h")
    print(f"  Bad sectors: {data.bad_sectors} ({data.bad_kb} KB)")
    print(f"  Files carved: {data.total_files} ({data.carving_pct:.1f}%)")
    print(f"  Types: JPG={data.jpg} MP4={data.mp4} PNG={data.png} MOV={data.mov} GIF={data.gif}")
    print(f"  ETA: {data.eta_h:.1f}h | Efficiency: {data.efficiency:.2f} GB/h")
    print(f"  Vitality: {data.vitality:.2f} | Chaos: {data.chaos:.2f}")
    print(f"  Dreaminess: {data.dreaminess:.2f} | Corruption: {data.corruption:.3f}")
    print(f"  Type entropy: {data.type_entropy:.2f} | Rarity: {data.type_rarity:.2f}")
    print(f"{'='*60}")

    arranger = VaporwaveArranger(data, bpm=args.bpm, length_sec=args.length)
    left, right = arranger.render_to_stereo()

    stereo = np.column_stack([left, right]).astype(np.float32)
    peak = np.max(np.abs(stereo))
    if peak > 0.98:
        stereo *= 0.95 / peak
    stereo_int16 = (stereo * 32767).astype(np.int16)

    with wave.open(args.out, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(stereo_int16.tobytes())

    size_mb = os.path.getsize(args.out) / 1024 / 1024
    root_name = note_name(arranger.map.root_midi)
    print(f"\n{'='*60}")
    print(f"  ✅ RENDERED → {args.out}")
    print(f"  Size: {size_mb:.1f} MB | {SAMPLE_RATE/1000:.0f}kHz / 16bit / Stereo")
    print(f"  Length: {args.length}s | BPM: {arranger.map.bpm}")
    print(f"  Key: {root_name} {arranger.map.scale}")
    print(f"  Progression: {arranger.map.prog_name}")
    print(f"  Chord quality: {arranger.map.chord_quality}")
    print(f"  Peak: {peak:.3f} | RMS: {np.sqrt(np.mean(stereo**2)):.3f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
