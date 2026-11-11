"""'The breakup' - 30 s chat reel.  Single source of truth for the script and all timing.

Music: Lewis Capaldi - Someone You Loved (30 s preview), natural speed:
  * hit at 6.93 s  -> the "47 min later" slam; the track then drops to near-silence (dialogue breathes)
  * dips again at 16-17 s ("I know when you're sad"), builds from 18 s
  * hit at 24.88 s -> the finger presses BLOCK
"""
import zlib

import numpy as np

FPS = 30
DURATION = 30.0
TOTAL_FRAMES = int(DURATION * FPS)

SWELL = 6.93            # music hit == "47 min later" slams in
BLOCK_HIT = 24.88       # music hit == finger presses Block

# ------------------------------------------------------------------ chat
# side: "ig" (Instagram, left) | "me" (you, right) | "ts" (timestamp label) | "fail" (undelivered IG message)
# type_start: when the typing dots (ig) or the keystrokes (me) begin;  show: when the bubble lands
MSGS = [
    dict(side="ts", text="Today 12:25 AM", show=0.0),
    dict(side="ig", text="hey. you up?", type_start=0.20, show=0.80),
    dict(side="me", text="I told you I'm done.", type_start=1.80, show=2.95),
    dict(side="ig", text="lol, you said that yesterday.", type_start=3.35, show=4.20),
    dict(side="ig", text="just one reel. 2 minutes.", type_start=4.80, show=5.65),
    # ---- time skip (6.30 - 8.40) ----
    dict(side="ts", text="Today 1:12 AM", show=8.45),
    dict(side="me", text="I feel worse every time.", type_start=8.90, show=10.25),
    dict(side="ig", text="but you came back.", type_start=10.85, show=11.80),
    dict(side="ig", text="I know when you're sad.", type_start=14.00, show=14.85),
    dict(side="ig", text="1:12 am?", type_start=15.50, show=16.15),
    dict(side="me", text="stop.", type_start=17.15, show=17.95),
    dict(side="ig", text="you can't block me.", type_start=19.00, show=19.80),
    dict(side="ig", text="you'll be back in 4 minutes.", type_start=20.55, show=21.60),
    # ---- block (finger, alert, lock card) ----
    dict(side="fail", text="wait—", type_start=25.85, show=26.30),
]

# ------------------------------------------------------------------ phone clock
CLOCK = [(0.0, "12:25"), (7.60, "1:12"), (22.40, "1:13")]

# ------------------------------------------------------------------ time skip
SKIP_IN = 6.05           # chat dims
SKIP_SLAM = SWELL        # "47 min later" hits with the music
SKIP_OUT = 8.30          # chat comes back

# ------------------------------------------------------------------ tension + block
TENSION_IN = 19.0        # red vignette + heartbeat start
FINGER_IN = 22.25        # touch indicator appears
INFO_TAP = 23.15         # taps the (i) in the header
ALERT_IN = 23.30         # "Block Instagram?" alert
BLOCK_TAP = BLOCK_HIT    # presses Block
LOCK_IN = BLOCK_TAP + 0.10       # big "blocked until 8:00" card
LOCK_OUT = 25.85                 # card dissolves into the locked input bar
KEYBOARD_DOWN = (BLOCK_TAP + 0.05, BLOCK_TAP + 0.45)
FAIL_TYPING = 25.85
FAIL_SHOW = 26.30
CTA_IN = 27.0

TIMELINE_LABELS = {"time_skip": (SKIP_IN, SKIP_OUT), "block": (INFO_TAP, LOCK_OUT)}


def key_times(m):
    """deterministic keystroke times for one of your messages (used by picture AND sound)"""
    n = len(m["text"])
    t0, t1 = m["type_start"], m["show"] - 0.14
    rs = np.random.default_rng(zlib.crc32(m["text"].encode()))
    gaps = 0.8 + 0.4 * rs.random(n)
    cum = np.cumsum(gaps)
    return t0 + (t1 - t0) * (cum - gaps[0]) / max(1e-6, cum[-1] - gaps[0])
