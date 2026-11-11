"""Soundtrack of the film: room tone + phone-in-hand sounds for the prologue, then the chat's own sound design
(breakup/sound.py) shifted into place, and a very quiet instrumental bed (Hans Zimmer - Time, looped)."""
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "breakup"))
import sound as bs          # noqa: E402
import script as CS         # noqa: E402
import film as F            # noqa: E402

SR = bs.SR
lw = bs.lw
place = lw.place
rng = np.random.default_rng(21)


def room_tone(dur):
    n = int(dur * SR)
    x = np.cumsum(rng.standard_normal(n))
    x -= np.convolve(x, np.ones(2000) / 2000, mode="same")           # brown noise, rumble removed
    x /= np.abs(x).max()
    hiss = lw.hp(rng.standard_normal(n), 6000) * 0.05
    t = np.arange(n) / SR
    hum = 0.015 * np.sin(2 * np.pi * 50 * t) + 0.01 * np.sin(2 * np.pi * 100 * t)
    return 0.05 * x + hiss * 0.12 + hum


def build_sfx(total):
    buf = np.zeros((int(total * SR), 2))
    n_room = int((F.OPEN_T + 1.0) * SR)
    rt = room_tone(F.OPEN_T + 1.0)
    env = np.ones(n_room)
    env[:int(0.8 * SR)] = np.linspace(0, 1, int(0.8 * SR))
    env[-int(1.6 * SR):] = np.linspace(1, 0, int(1.6 * SR))
    buf[:n_room, 0] += rt * env
    buf[:n_room, 1] += rt * env
    # thumb swipes on the feed (a swipe every 1.45 s, 0.3 s long, from 1.15 s)
    k = 1
    while k * 1.45 - 0.30 < F.PUSH0 + 0.2:
        ts = k * 1.45 - 0.30
        place(buf, lw.whoosh(0.26, True, 0.10, 600, 4500), ts)
        place(buf, lw.tick(1500, 0.03, 0.07), ts + 0.02)
        place(buf, lw.thud(90, 0.14, 0.10), ts + 0.20)
        k += 1
    # match cut wide -> close
    place(buf, lw.whoosh(0.45, True, 0.24, 300, 6500), F.A_END - 0.30)
    place(buf, lw.thud(66, 0.32, 0.55), F.A_END)
    # the message arrives: haptic buzz + chime
    for d in (0.0, 0.17):
        place(buf, bs.buzz(0.12, 78, 0.45), F.NOTIF_T + d)
    place(buf, bs.recv(1.2), F.NOTIF_T + 0.02)
    # the camera flies into the screen
    place(buf, lw.riser(F.PUSH1 - F.PUSH0 + 0.05, 0.50, 180, 2800), F.PUSH0 - 0.02)
    place(buf, lw.whoosh(1.0, True, 0.26, 250, 6500), F.PUSH0 + 0.12)
    place(buf, lw.boom(1.6, 80, 38, 0.60), F.PUSH1)
    # tap + open
    place(buf, bs.click(0.40, 120), F.TAP_T)
    place(buf, bs.ping(1480, 0.3, 0.16), F.TAP_T + 0.02)
    place(buf, lw.whoosh(0.22, True, 0.20, 700, 5500), F.OPEN_T - 0.04)
    # the chat's sound design, from chat time 0.8 s on
    csfx = bs.build_sfx(CS.DURATION + 0.15)
    a = int(F.CHAT_SHIFT * SR)
    seg = csfx[a:]
    o = int(F.OPEN_T * SR)
    n = min(len(seg), len(buf) - o)
    buf[o:o + n] += seg[:n]
    return buf


def load_loop(path, n):
    m = lw.load_audio(path, 1.0, stereo=True)
    out = m
    xf = int(2.5 * SR)
    while len(out) < n:
        seg = m[int(5 * SR):]
        fo = np.cos(np.linspace(0, np.pi / 2, xf))[:, None]
        fi = np.sin(np.linspace(0, np.pi / 2, xf))[:, None]
        out = np.vstack([out[:-xf], out[-xf:] * fo + seg[:xf] * fi, seg[xf:]])
    return out[:n]


def music_gain(total):
    t = np.arange(int(total * SR)) / SR
    pro = np.interp(t, [0, 0.8, 4.0, F.NOTIF_T, F.PUSH0, F.PUSH1, F.OPEN_T + 0.1, F.OPEN_T + 0.8],
                    [0.0, 0.05, 0.08, 0.09, 0.12, 0.20, 0.07, 0.015])
    ct = t - (F.OPEN_T - F.CHAT_SHIFT)
    cg = bs.music_gain(CS.DURATION + 0.15)
    idx = np.clip((ct * SR).astype(int), 0, len(cg) - 1)
    chat = cg[idx] * bs.MUSIC_LEVEL
    g = np.where(t < F.OPEN_T + 0.8, pro, chat)
    g[-int(1.2 * SR):] *= np.linspace(1, 0, int(1.2 * SR))
    return g


def build_mix(path, with_music=True):
    total = F.TOTAL + 0.15
    sfx = build_sfx(total)
    if with_music:
        m = load_loop(os.path.join(HERE, "..", "breakup", "assets", "music", "time.mp3"), int(total * SR))
        mix = m * music_gain(total)[:, None] * 0.95 + sfx * 0.90
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
    build_mix(sys.argv[1] if len(sys.argv) > 1 else "film_mix.wav")
