"""Soundtrack for 'The breakup': synthesised chat sounds + Luminary under it.

Everything is placed from script.py, so picture and sound cannot drift apart.
Music: Hans Zimmer - Time (30 s preview, instrumental) as a quiet underscore. It has no hits of its own,
so the two big moments (6.93 s "47 min later", 24.88 s Block) are made by the synthesised impacts.
"""
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "life_in_weeks"))
import audio as lw          # noqa: E402  (synth primitives shared with the other reel)
import script as S          # noqa: E402

SR = lw.SR
rng = np.random.default_rng(3)
place, thud, boom, crash, whoosh, blip, bell, tick = lw.place, lw.thud, lw.boom, lw.crash, lw.whoosh, lw.blip, lw.bell, lw.tick
tt, hp, lp, env_exp = lw.tt, lw.hp, lw.lp, lw.env_exp


def click(gain=0.2, f=150):
    t = tt(0.05)
    n = hp(rng.standard_normal(len(t)), 2200) * env_exp(t, 380, 0.0003)
    body = np.sin(2 * np.pi * f * t) * env_exp(t, 140, 0.0005)
    return gain * (0.8 * n / (np.abs(n).max() + 1e-9) + 0.9 * body)


def recv(gain=1.0):
    """incoming message: soft two-note chime + haptic thump"""
    a = bell(1568.0, 0.55, 0.20 * gain)
    b = np.concatenate([np.zeros(int(0.075 * SR)), bell(2093.0, 0.45, 0.13 * gain)])
    n = max(len(a), len(b))
    out = np.zeros(n)
    out[:len(a)] += a
    out[:len(b)] += b
    t = tt(0.14)
    hap = np.sin(2 * np.pi * 78 * t) * env_exp(t, 24, 0.002) * 0.34 * gain
    out[:len(hap)] += hap
    return out


def send(gain=1.0):
    w = whoosh(0.16, True, 0.14 * gain, 700, 5500)
    t = tt(0.11)
    pop = np.sin(2 * np.pi * (660 + 260 * np.exp(-t * 40)) * t) * env_exp(t, 32, 0.001) * 0.30 * gain
    out = np.zeros(len(w) + len(pop))
    out[:len(w)] += w
    out[len(w) - int(0.04 * SR):len(w) - int(0.04 * SR) + len(pop)] += pop
    return out


def ping(freq, dur=0.5, gain=0.3):
    t = tt(dur)
    return gain * (np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2.76 * t)) * env_exp(t, 9, 0.0005)


def buzz(dur=0.12, f=118, gain=0.4):
    t = tt(dur)
    s = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(2 * np.pi * f * t) * 0.5
    return gain * s * np.minimum(1, t / 0.004) * np.minimum(1, (dur - t) / 0.01)


def drone(dur, gain=0.5):
    t = tt(dur)
    p = t / dur
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * (0.6 + 1.6 * p) * t)
    tone = np.sin(2 * np.pi * 55 * t) + 0.6 * np.sin(2 * np.pi * 82.4 * t) + 0.25 * np.sin(2 * np.pi * 110.7 * t)
    bed = lp(rng.standard_normal(len(t)), 260) * 3.0
    return gain * (tone * 0.5 + bed * 0.5) * trem * p ** 1.6


def build_sfx(total):
    buf = np.zeros((int(total * SR), 2))

    # ---- chat: typing / sending / receiving
    for m in S.MSGS:
        if m["side"] == "ts":
            continue
        if m["side"] == "me":
            for i, kt in enumerate(S.key_times(m)):
                ch = m["text"][i]
                place(buf, click(0.20 if ch != " " else 0.26, 150 if ch != " " else 110), kt, 1.0, pan=0.0)
            place(buf, send(), m["show"] - 0.02)
        else:
            place(buf, blip(1040, 0.05, 0.10), m["type_start"])            # dots appear
            if m["side"] == "ig":
                place(buf, recv(), m["show"])
    place(buf, boom(1.4, 70, 40, 0.30), 0.0)                              # open: low thump

    # ---- time skip: accelerating clock ticks, reversed crash, slam on the music's swell peak
    n_ticks, t0, t1 = 14, S.SKIP_IN + 0.15, S.SWELL - 0.05
    for i in range(n_ticks):
        x = (i / (n_ticks - 1)) ** 1.8
        place(buf, tick(1900 if i % 2 == 0 else 1500, 0.03, 0.22), t0 + (t1 - t0) * x)
    rc = crash(1.0, 2800, 2.4, 0.5)[::-1]
    place(buf, rc, S.SWELL - 1.0)
    place(buf, boom(2.2, 90, 36, 0.8), S.SWELL)
    place(buf, crash(1.2, 2400, 3.0, 0.45), S.SWELL)
    place(buf, whoosh(0.5, False, 0.3, 300, 7000), S.SWELL + 0.02)
    place(buf, tick(1700, 0.04, 0.2), S.CLOCK[1][0])                       # status-bar clock flips
    place(buf, tick(1250, 0.05, 0.16), S.CLOCK[1][0] + 0.09)
    place(buf, whoosh(0.4, True, 0.2), S.SKIP_OUT - 0.1)

    # ---- tension: drone + heartbeat that speeds up
    place(buf, drone(S.BLOCK_TAP - S.TENSION_IN, 0.55), S.TENSION_IN)
    t = S.TENSION_IN + 0.3
    while t < S.BLOCK_TAP - 0.2:
        ramp = (t - S.TENSION_IN) / (S.BLOCK_TAP - S.TENSION_IN)
        g = 0.35 + 0.55 * ramp
        place(buf, thud(52, 0.30, 0.95 * g), t)
        place(buf, thud(46, 0.26, 0.60 * g), t + 0.17)
        t += 60.0 / (62 + 30 * ramp)

    # ---- finger, alert, BLOCK
    place(buf, whoosh(0.35, True, 0.14, 500, 4500), S.FINGER_IN - 0.05)
    place(buf, click(0.30, 120), S.INFO_TAP)
    place(buf, ping(1480, 0.3, 0.18), S.INFO_TAP + 0.02)
    place(buf, whoosh(0.2, True, 0.2, 700, 5000), S.ALERT_IN - 0.02)
    place(buf, thud(80, 0.2, 0.5), S.ALERT_IN)
    place(buf, click(0.35, 110), S.BLOCK_TAP - 0.012)                      # the tap
    place(buf, boom(2.6, 95, 32, 1.0), S.BLOCK_TAP)
    place(buf, crash(1.6, 2000, 2.8, 0.75), S.BLOCK_TAP)
    place(buf, ping(2637, 0.7, 0.18), S.BLOCK_TAP + 0.01)                  # glass-like ring
    place(buf, whoosh(0.4, False, 0.28, 300, 6500), S.BLOCK_TAP + 0.02)

    # ---- lock card: two metal clacks, then the failed message
    place(buf, ping(1180, 0.25, 0.30), S.LOCK_IN + 0.10)
    place(buf, click(0.45, 200), S.LOCK_IN + 0.10)
    place(buf, ping(880, 0.30, 0.30), S.LOCK_IN + 0.26)
    place(buf, click(0.50, 90), S.LOCK_IN + 0.26)
    place(buf, boom(1.0, 60, 38, 0.45), S.LOCK_IN + 0.26)
    place(buf, blip(1040, 0.05, 0.10), S.FAIL_TYPING)
    place(buf, buzz(0.11, 118, 0.42), S.FAIL_SHOW)                         # "Not delivered"
    place(buf, buzz(0.11, 98, 0.42), S.FAIL_SHOW + 0.17)
    place(buf, ping(330, 0.5, 0.22), S.FAIL_SHOW + 0.03)

    # ---- CTA
    place(buf, whoosh(0.45, True, 0.30, 400, 7000), S.CTA_IN - 0.15)
    place(buf, boom(1.4, 85, 40, 0.55), S.CTA_IN)
    for i, f in enumerate((440.0, 554.4, 659.3, 880.0)):
        place(buf, bell(f, 1.8, 0.16), S.CTA_IN + 0.12 + 0.11 * i)
    place(buf, thud(70, 0.3, 0.8), S.CTA_IN + 0.30)                        # BLOCK pill lands
    place(buf, tick(2200, 0.03, 0.18), S.CTA_IN + 0.62)
    place(buf, tick(2000, 0.03, 0.14), S.CTA_IN + 0.80)
    return buf


MUSIC_LEVEL = 0.45          # overall music level (0.95 was the first version; lower = quieter)


def music_gain(total):
    """instrumental underscore: barely there under the typing and messages, swelling into the two big
    moments (the "47 min later" slam and the Block tap) and ducked away for the lock card."""
    key = [(0.0, 0.16), (4.0, 0.22), (S.SWELL - 0.6, 0.30), (S.SWELL, 0.50), (S.SWELL + 0.6, 0.26), (9.0, 0.22),
           (16.0, 0.22), (19.0, 0.27), (22.5, 0.36), (24.3, 0.48), (S.BLOCK_TAP, 0.62), (S.BLOCK_TAP + 0.25, 0.10),
           (26.3, 0.12), (26.9, 0.20), (S.CTA_IN + 0.1, 0.46), (28.6, 0.50), (total, 0.0)]
    ts, gs = zip(*key)
    t = np.arange(int(total * SR)) / SR
    return np.interp(t, ts, gs)


def build_mix(path, with_music=True):
    total = S.DURATION + 0.15
    sfx = build_sfx(total)
    if with_music:
        m = lw.load_audio(os.path.join(HERE, "assets", "music", "time.mp3"), 1.0, stereo=True)
        n = int(total * SR)
        m = m[:n] if len(m) >= n else np.vstack([m, np.zeros((n - len(m), 2))])
        mix = m * music_gain(total)[:, None] * MUSIC_LEVEL + sfx * 0.90
    else:
        mix = sfx * 1.15
    mix = np.tanh(mix * 0.9) / np.tanh(0.9)
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    build_mix(sys.argv[1] if len(sys.argv) > 1 else "mix.wav")
