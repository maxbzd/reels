"""Synthesised sound design for the reel (pure numpy, no samples, no licences).

All event times come from timeline.py so picture and sound stay in sync.
Writes a stereo 44.1 kHz wav containing ONLY the effects; the music is mixed
in by build.py with ffmpeg.
"""
import wave

import numpy as np

import timeline as T

SR = 44100
rng = np.random.default_rng(7)


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def blip(freq, dur=0.12, gain=0.5):
    t = _t(dur)
    env = np.exp(-t * 38) * np.minimum(1, t * 600)
    return gain * env * (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * 2 * freq * t))


def bell(freq, dur=1.6, gain=0.35):
    t = _t(dur)
    env = np.exp(-t * 2.8) * np.minimum(1, t * 300)
    out = np.zeros_like(t)
    for mult, g in ((1, 1.0), (2.01, 0.45), (3.02, 0.22), (4.2, 0.1)):
        out += g * np.sin(2 * np.pi * freq * mult * t)
    return gain * env * out / 1.8


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def noise_sweep(dur, f0, f1, gain, shape="up"):
    """Band-ish noise whose brightness sweeps f0 -> f1 (one-pole lowpass, vectorised in blocks)."""
    n = int(dur * SR)
    x = rng.standard_normal(n)
    block = 256
    out = np.zeros(n)
    acc = 0.0
    for b in range(0, n, block):
        p = b / n
        fc = f0 * (f1 / f0) ** p
        a = np.exp(-2 * np.pi * fc / SR)
        seg = x[b:b + block]
        # tiny loop per block keeps this simple and fast enough
        y = np.empty_like(seg)
        for i, v in enumerate(seg):
            acc = (1 - a) * v + a * acc
            y[i] = acc
        out[b:b + block] = y
    out -= np.convolve(out, np.ones(64) / 64, mode="same")  # crude high-pass: remove rumble
    t = np.linspace(0, 1, n)
    env = t ** 2.2 if shape == "up" else np.sin(np.pi * t) ** 1.5
    return gain * env * out / (np.abs(out).max() + 1e-9)


def riser(dur, gain=0.5):
    t = _t(dur)
    p = t / dur
    f = 180 * (9 ** p)
    phase = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(phase) * (p ** 2.5)
    return gain * (0.45 * tone) + noise_sweep(dur, 400, 6500, gain * 0.55, "up")


def impact(gain=0.9):
    t = _t(1.8)
    sub = np.sin(2 * np.pi * (46 + 60 * np.exp(-t * 14)) * t) * np.exp(-t * 2.2)
    clap = lowpass(rng.standard_normal(len(t)), 2500) * np.exp(-t * 14)
    return gain * (0.9 * sub + 0.5 * clap)


def whoosh(dur=0.32, gain=0.16):
    return noise_sweep(dur, 500, 5200, gain, shape="bell")


def place(buf, sig, at, pan=0.0):
    i = int(at * SR)
    n = min(len(sig), len(buf) - i)
    if n <= 0:
        return
    l, r = (1 - max(pan, 0)), (1 + min(pan, 0))
    buf[i:i + n, 0] += sig[:n] * l
    buf[i:i + n, 1] += sig[:n] * r


def build(path):
    total = T.TOTAL_SEC + 0.5
    buf = np.zeros((int(total * SR), 2))

    # grid appears + every category reveal
    place(buf, blip(1320, 0.14, 0.35), T.GRID_IN)
    for s in T.STEPS:
        f = 330 if s["key"] == "screens" else 880 + 60 * s["idx"]
        place(buf, blip(f, 0.14, 0.45), s["t0"])
        if s["key"] == "screens":          # warning: second lower blip
            place(buf, blip(262, 0.2, 0.45), s["t0"] + 0.16)
    # fill ticks: soft rolling pulses while a block fills
    for s in T.STEPS:
        n = 9
        for k in range(n):
            place(buf, blip(2400 + 40 * k, 0.03, 0.06), s["t0"] + 0.1 + k * (T.FILL_DUR / n))

    # signal loss
    for k, tt in enumerate(T.SIGNAL_TIMES):
        place(buf, blip(700 - 90 * k, 0.1, 0.25), tt)

    # riser into the drop, then impact
    place(buf, riser(T.DROP - T.RISER_START, 0.5), T.RISER_START)
    place(buf, impact(), T.DROP - 0.015)

    # whoosh on every cut after the drop
    for c in T.CUTS[1:]:
        place(buf, whoosh(), c - 0.08, pan=0.0)

    # battery reaches 100%
    place(buf, bell(1318.5, 1.8, 0.30), T.FULL_TIME)
    place(buf, bell(1976.0, 1.4, 0.18), T.FULL_TIME + 0.09)

    buf = np.clip(buf, -1, 1)
    pcm = (buf * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else "sfx.wav")
