"""Whole soundtrack: music + synthesised sound design + voice-over.

Everything is numpy @ 44.1 kHz stereo, event times come from timeline.py.
  * music      : assets/music/luminary.mp3, ducked under the voice, "sucked out"
                 for a split second before the drop, faded at the end
  * sound FX   : pure synthesis (no samples -> no licences)
  * voice-over : ElevenLabs lines (assets/vo11), trimmed to speech onset,
                 levelled, lightly reverbed
Output: stereo wav, loudness-normalised later by ffmpeg when muxing.
"""
import os
import subprocess
import wave

import numpy as np
from scipy.signal import butter, sosfilt

import timeline as T

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
rng = np.random.default_rng(7)


# ---------------------------------------------------------------- primitives
def tt(d):
    return np.arange(int(d * SR)) / SR


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "hp", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "lp", fs=SR, output="sos"), x)


def sweep_noise(dur, f0, f1, bw=1.2):
    """noise whose spectral centre glides f0 -> f1 (STFT overlap-add, click-free)."""
    n = int(dur * SR)
    N, hop = 2048, 512
    x = rng.standard_normal(n + N)
    out = np.zeros(n + N)
    win = np.hanning(N)
    freqs = np.fft.rfftfreq(N, 1 / SR)
    for i in range(0, n, hop):
        p = i / max(1, n)
        fc = f0 * (f1 / f0) ** p
        mask = np.exp(-0.5 * (np.log2(np.maximum(freqs, 20) / fc) / (bw / 2)) ** 2)
        seg = np.fft.irfft(np.fft.rfft(x[i:i + N] * win) * mask)
        out[i:i + N] += seg * win
    out = out[:n]
    return out / (np.abs(out).max() + 1e-9)


def env_exp(t, k, attack=0.002):
    return np.exp(-t * k) * np.minimum(1, t / attack)


def boom(dur=2.0, f0=95, f1=36, gain=1.0):
    t = tt(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 9)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env_exp(t, 1.9, 0.004)
    thump = lp(rng.standard_normal(len(t)), 220) * env_exp(t, 18, 0.001) * 3
    return gain * (body + 0.5 * thump / (np.abs(thump).max() + 1e-9))


def crash(dur=1.8, lo=2500, k=2.6, gain=0.6):
    t = tt(dur)
    n = hp(rng.standard_normal(len(t)), lo)
    return gain * n / (np.abs(n).max() + 1e-9) * env_exp(t, k, 0.003)


def clap(gain=0.6):
    t = tt(0.4)
    n = hp(lp(rng.standard_normal(len(t)), 7000), 900)
    return gain * n / (np.abs(n).max() + 1e-9) * env_exp(t, 16, 0.001)


def thud(f=62, dur=0.35, gain=0.8):
    t = tt(dur)
    fr_ = f * (1 + 1.2 * np.exp(-t * 40))
    ph = 2 * np.pi * np.cumsum(fr_) / SR
    return gain * np.sin(ph) * env_exp(t, 11, 0.002)


def tick(freq=1800, dur=0.05, gain=0.3):
    t = tt(dur)
    return gain * np.sin(2 * np.pi * freq * t) * env_exp(t, 70, 0.0005)


def blip(freq, dur=0.14, gain=0.4):
    t = tt(dur)
    return gain * (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t)) * env_exp(t, 30, 0.001)


def beep(freq, dur=0.11, gain=0.35):
    t = tt(dur)
    s = np.sign(np.sin(2 * np.pi * freq * t)) * 0.4 + np.sin(2 * np.pi * freq * t) * 0.6
    e = np.minimum(1, t / 0.003) * np.minimum(1, (dur - t) / 0.01)
    return gain * s * e


def bell(freq, dur=1.8, gain=0.3):
    t = tt(dur)
    out = np.zeros_like(t)
    for mult, g in ((1, 1.0), (2.01, 0.45), (3.02, 0.22), (4.2, 0.1)):
        out += g * np.sin(2 * np.pi * freq * mult * t)
    return gain * env_exp(t, 2.6, 0.002) * out / 1.8


def whoosh(dur=0.3, up=True, gain=0.35, lo=400, hi=6500):
    s = sweep_noise(dur, lo, hi, 1.6) if up else sweep_noise(dur, hi, lo, 1.6)
    t = np.linspace(0, 1, len(s))
    return gain * s * np.sin(np.pi * t) ** 1.4


def riser(dur, gain=0.6, f_start=180, f_end=2400):
    t = tt(dur)
    p = t / dur
    f = f_start * (f_end / f_start) ** p
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) * p ** 2.2
    shimmer = sweep_noise(dur, 500, 9000, 1.8) * p ** 2.0
    trem = 0.7 + 0.3 * np.sin(2 * np.pi * (6 + 18 * p) * t)
    return gain * (0.35 * tone * trem + 0.8 * shimmer)


def static(dur, gain=0.2, lo=2000):
    t = tt(dur)
    n = hp(rng.standard_normal(len(t)), lo)
    gate = (rng.random(int(dur * 80) + 2) > 0.45).astype(float)
    g = np.interp(t, np.linspace(0, dur, len(gate)), gate)
    return gain * n / (np.abs(n).max() + 1e-9) * g * np.minimum(1, t / 0.005)


def shutter(gain=0.5):
    t = tt(0.09)
    n = hp(rng.standard_normal(len(t)), 1800) * env_exp(t, 90, 0.0005)
    n2 = np.zeros_like(t)
    j = int(0.045 * SR)
    n2[j:] = (hp(rng.standard_normal(len(t) - j), 1200) * env_exp(t[:len(t) - j], 110, 0.0005))
    return gain * (n + 0.7 * n2) / 1.6


def place(buf, sig, at, gain=1.0, pan=0.0):
    i = int(round(at * SR))
    if i < 0:
        sig = sig[-i:]
        i = 0
    n = min(len(sig), len(buf) - i)
    if n <= 0:
        return
    l, r = gain * (1 - max(pan, 0)), gain * (1 + min(pan, 0))
    buf[i:i + n, 0] += sig[:n] * l
    buf[i:i + n, 1] += sig[:n] * r


# -------------------------------------------------------------- sound design
def build_sfx(total):
    buf = np.zeros((int(total * SR), 2))
    # --- 0. hook: heartbeat thumps under "You're 20."
    place(buf, thud(55, 0.5, 1.0), 0.00)
    place(buf, thud(48, 0.5, 0.75), 0.30)
    place(buf, boom(1.2, 80, 40, 0.5), 0.0)

    # --- 1. grid rolls in: rising shimmer + sparkle ticks
    place(buf, sweep_noise(0.7, 900, 7500, 1.4) * np.linspace(0, 1, int(0.7 * SR)) ** 1.5 * 0.35, T.GRID_IN)
    for k in range(10):
        place(buf, tick(2200 + 140 * k, 0.04, 0.12), T.GRID_IN + 0.06 * k)

    # --- 2. count-up of "4,160 weeks"
    for k in range(12):
        place(buf, tick(1200 + 90 * k, 0.03, 0.1), T.COUNT_IN + 0.05 * k)

    # --- 3. every block: sub thud + rolling counter ticks
    for s in T.STEPS:
        g = 1.0 if s["key"] != "living" else 0.8
        place(buf, thud(60 - 2 * s["idx"], 0.4, 0.9 * g), s["t0"])
        place(buf, blip(660 * (1.12246 ** (s["idx"] * 2)), 0.16, 0.30), s["t0"])
        n = 11
        for k in range(n):
            place(buf, tick(2600 + 90 * k, 0.025, 0.08), s["t0"] + T.FILL_DELAY + k * (T.FILL_DUR / n))
        place(buf, whoosh(0.25, True, 0.16), s["t0"] - 0.02)

    # --- 4. screens = alarm: low drone + warning beeps + low-battery chirps
    sc = T.STEPS[3]
    for i in range(4):
        place(buf, beep(880 if i % 2 == 0 else 660, 0.10, 0.28), sc["t0"] + 0.08 + 0.17 * i)
    place(buf, boom(1.0, 70, 48, 0.55), sc["t0"] + 0.05)
    low = sc["t0"] + 0.55
    for i in range(3):
        place(buf, beep(1480, 0.07, 0.22), low + 0.14 * i)

    # --- 5. signal dies: falling blips + growing static
    for k, ts in enumerate(T.SIGNAL_TIMES):
        place(buf, blip(900 - 140 * k, 0.12, 0.30), ts)
        place(buf, static(0.28, 0.10 + 0.07 * k), ts)

    # --- 6. build to the drop (reverse crash + riser), then the HIT
    place(buf, riser(1.82, 0.7, 220, 3200), T.DROP - 1.8)
    rc = crash(1.4, 3000, 2.0, 0.7)[::-1]
    place(buf, rc[-int(1.4 * SR):], T.DROP - 1.4)
    place(buf, boom(2.6, 100, 34, 1.0), T.DROP)
    place(buf, crash(1.8, 2500, 2.4, 0.75), T.DROP)
    place(buf, clap(0.7), T.DROP)
    place(buf, whoosh(0.5, False, 0.35, 300, 8000), T.DROP)

    # --- 7. montage: a whoosh + thud at every cut, shutter clicks on rapid-fire shots
    for i, c in enumerate(T.CUTS):
        if i == 0:
            continue
        flash = len(T.SHOTS[i][4]) == 0
        place(buf, whoosh(0.22 if flash else 0.3, True, 0.30, 500, 7500), c - 0.10)
        place(buf, thud(70, 0.22, 0.45 if flash else 0.6), c)
        if flash:
            place(buf, shutter(0.5), c)
        else:
            place(buf, tick(2400, 0.03, 0.18), c + 0.08)       # caption "pop"

    # --- 8. accent on "The phone can wait."
    place(buf, boom(1.4, 90, 40, 0.7), T.PHONE_SHOT_START)
    place(buf, crash(1.0, 3000, 3.6, 0.45), T.PHONE_SHOT_START)

    # --- 9. final line: pre-hit riser + big impact
    place(buf, riser(0.9, 0.55, 300, 3000), T.FINAL_SHOT_START - 0.9)
    place(buf, boom(3.0, 100, 32, 1.0), T.FINAL_SHOT_START)
    place(buf, crash(2.2, 2200, 2.0, 0.7), T.FINAL_SHOT_START)

    # --- 10. battery full: ding
    place(buf, bell(1318.5, 1.8, 0.34), T.FULL_TIME)
    place(buf, bell(1975.5, 1.4, 0.2), T.FULL_TIME + 0.09)

    # --- 11. call-to-action card: soft swell + low chime
    place(buf, whoosh(0.45, True, 0.30, 300, 6000), T.CTA_AT - 0.12)
    place(buf, bell(659.3, 1.8, 0.22), T.CTA_AT)
    return buf


# --------------------------------------------------------------- voice-over
def load_audio(path, tempo=1.0, stereo=False, max_dur=None, ss=None, dur=None):
    af = []
    if tempo != 1.0:
        af.append(f"atempo={tempo}")
    cmd = ["ffmpeg", "-v", "error"]
    if ss is not None:
        cmd += ["-ss", f"{ss}"]
    if dur is not None:
        cmd += ["-t", f"{dur}"]
    cmd += ["-i", path]
    if af:
        cmd += ["-af", ",".join(af)]
    cmd += ["-ac", "2" if stereo else "1", "-ar", str(SR), "-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).copy()
    if stereo:
        x = x.reshape(-1, 2)
    return x


def reverb(x, rt=0.9, wet=0.16, predelay=0.02):
    n = int(rt * 1.3 * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 6.9 / rt)
    ir = lp(ir, 5500)
    ir[:int(predelay * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n
    nfft = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(x)]
    return x + wet * y * np.abs(x).max() / (np.abs(y).max() + 1e-9) * 3.0


def build_vo(total):
    bus = np.zeros(int(total * SR))
    for rel, onset, tempo, max_dur in T.VO:
        x = load_audio(os.path.join(ASSETS, rel), tempo)
        pk = np.abs(x).max() + 1e-9
        i0 = int(np.argmax(np.abs(x) > 0.05 * pk))
        x = x[i0:]
        if max_dur:
            x = x[:int(max_dur * SR / 1.0)]
        # fades
        fi, fo = int(0.004 * SR), int(0.03 * SR)
        x[:fi] *= np.linspace(0, 1, fi)
        x[-fo:] *= np.linspace(1, 0, fo)
        # level: aim at a consistent RMS, then soft-limit
        rms = np.sqrt(np.mean(x ** 2)) + 1e-9
        x = np.tanh(x / rms * 0.20 * 1.6) / 1.6 * 1.0
        j = int(round(onset * SR))
        n = min(len(x), len(bus) - j)
        bus[j:j + n] += x[:n]
    bus = hp(bus, 80)
    bus = reverb(bus)
    bus *= 0.9 / (np.abs(bus).max() + 1e-9)
    return bus


# -------------------------------------------------------------------- music
def smooth_env(sig, win_s):
    k = int(win_s * SR)
    w = np.hanning(k)
    w /= w.sum()
    return np.convolve(sig, w, "same")


def build_music(total, vo):
    """The track swells to a peak at 7.057 s; we stretch the lead-in so that peak lands on the
    flash at DROP (9.8 s).  After the drop the track plays at its natural speed."""
    path = os.path.join(ASSETS, "music", "luminary.mp3")
    n = int(total * SR)
    nd = int(round(T.DROP * SR))
    xf = int(0.03 * SR)
    lead = load_audio(path, T.LEAD_TEMPO, stereo=True, dur=T.MUSIC_DROP)
    lead = lead[:nd] if len(lead) >= nd else np.vstack([lead, np.zeros((nd - len(lead), 2))])
    rest = load_audio(path, 1.0, stereo=True, ss=T.MUSIC_DROP - 0.03)
    m = np.zeros((n, 2))
    m[:nd] = lead
    # equal-power crossfade at the join
    lead_tail = m[nd - xf:nd].copy()
    fo = np.cos(np.linspace(0, np.pi / 2, xf))[:, None]
    fi = np.sin(np.linspace(0, np.pi / 2, xf))[:, None]
    m[nd - xf:nd] = lead_tail * fo + rest[:xf] * fi
    tail = rest[xf:xf + (n - nd)]
    m[nd:nd + len(tail)] = tail
    g = np.ones(n)
    # duck under the voice
    e = smooth_env(np.abs(vo[:n]), 0.12)
    e = np.clip(e / (np.percentile(e[e > 1e-4], 90) + 1e-9), 0, 1)
    g *= 1 - 0.50 * smooth_env(e, 0.10)
    # split-second "suck-out" right before the drop
    a, b = (int(x * SR) for x in T.SUCKOUT)
    dip = np.ones(n)
    dip[a:b] = 0.04
    dip = smooth_env(dip, 0.012)
    g *= dip
    # gentle fade-out over the last 1.8 s (no abrupt cut)
    f0 = int((total - 1.8) * SR)
    g[f0:] *= np.cos(np.linspace(0, np.pi / 2, n - f0)) ** 2
    return m * g[:, None]


# ----------------------------------------------------------------------- mix
def build_mix(path, with_music=True):
    total = T.TOTAL_SEC + 0.15
    sfx = build_sfx(total)
    vo = build_vo(total)
    voice = np.stack([vo, vo], 1) * 1.15
    if with_music:
        mix = build_music(total, vo) * 0.80 + sfx * 0.50 + voice
    else:                                    # for adding a trending track inside Instagram
        mix = sfx * 0.75 + voice
    mix = np.tanh(mix * 0.8) / np.tanh(0.8)             # soft clip
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    # stems for debugging / checking the voice with speech recognition
    stem = os.path.join(os.path.dirname(path), "_vo_only.wav")
    v16 = (np.clip(vo, -1, 1) * 32767).astype("<i2")
    with wave.open(stem, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(v16.tobytes())


if __name__ == "__main__":
    import sys
    build_mix(sys.argv[1] if len(sys.argv) > 1 else "mix.wav")
