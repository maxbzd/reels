"""Single source of truth for timing + numbers (v2: short & fast, ~19.6 s).

Music: "Luminary" (Joel Sunny), ~67.4 BPM.  The beat grid was fitted on the
track: one *eighth note* E = 0.4451 s, phase 0.380 s.  The track swells to a
peak at the 15th eighth (7.057 s) - that is our DROP: the data-viz intro
slams into the footage exactly there.   30 fps  =>  E ~ 13.35 frames.
"""

FPS = 30
E = 0.4451
PHASE = 0.380


def tk(k):
    """time (s) of the k-th eighth note on the track's grid"""
    return PHASE + E * k


def fr(t):
    return int(round(t * FPS))


DROP = tk(15)                    # 7.057 s
DROP_FRAME = fr(DROP)

# ---------------------------------------------------------------- the maths
# Ages 0 -> 80.  One dot = one week.  (Rough numbers, shown in the footnote.)
WEEKS_PER_YEAR = 52
TOTAL_WEEKS = 80 * WEEKS_PER_YEAR               # 4160
GONE = 20 * WEEKS_PER_YEAR                      # 1040  (ages 0-20, "You're 20")
REMAINING = TOTAL_WEEKS - GONE                  # 3120  (60 years)
SLEEP = REMAINING // 3                          # 1040  (8 h/day = 1/3)
WORKCHORES = (9 + 10) * WEEKS_PER_YEAR          # 988   (~9 y work/school + ~10 y chores/commute)
SCREENS = REMAINING // 6                        # 520   (4 h/day = 1/6 of a day)
LIVING = REMAINING - SLEEP - WORKCHORES - SCREENS      # 572 weeks = 11 years
assert LIVING == 572 and GONE + SLEEP + WORKCHORES + SCREENS + LIVING == TOTAL_WEEKS

COLORS = {
    "gone": (118, 124, 140),
    "sleep": (140, 100, 255),
    "workchores": (255, 70, 160),
    "screens": (255, 110, 50),
    "living": (90, 255, 160),
}

FILL_DELAY = 0.03
FILL_DUR = 0.62
# key, grid step k (start), eighths it lasts, weeks, label, years shown
_defs = [
    ("gone",       4, 2, GONE,       "ALREADY GONE",                 20),
    ("sleep",      6, 2, SLEEP,      "ASLEEP",                       20),
    ("workchores", 8, 2, WORKCHORES, "WORK & CHORES",                19),
    ("screens",   10, 3, SCREENS,    "ON SCREENS  ·  4 HRS A DAY",   10),
    ("living",    13, 2, LIVING,     "LEFT TO ACTUALLY LIVE",        11),
]
STEPS = []
_off = 0
for i, (key, k, ne, n, label, yrs) in enumerate(_defs):
    STEPS.append(dict(idx=i, key=key, k=k, t0=tk(k), dur=ne * E, n=n, label=label, years=yrs,
                      start=_off, color=COLORS[key]))
    _off += n

# ------------------------------------------------------------- intro beats
TITLE_IN = 0.0                  # "You're 20." is on screen from the very first frame
TITLE_OUT = tk(2)               # 1.27 s
GRID_IN = tk(2) - 0.15          # dots roll in
COUNT_IN = tk(2) + 0.05         # "4,160 weeks" for one beat before the first block
COUNT_OUT = tk(4)

# signal bars degrade on the 4 eighths before the drop
SIGNAL_TIMES = [tk(11), tk(12), tk(13), tk(14)]
SIGNAL_STATES = [(0.0, "5G", 4), (SIGNAL_TIMES[0], "4G", 3), (SIGNAL_TIMES[1], "3G", 2),
                 (SIGNAL_TIMES[2], "", 1), (SIGNAL_TIMES[3], "", 0), (DROP, "No Service", 0)]
SUCKOUT = (DROP - 0.14, DROP)   # music dips just before the hit

# ------------------------------------------------------------ nature section
# (clip id, source start s, horizontal crop focus 0..1, eighths, caption lines)
SHOTS = [
    (32, 3.0, 0.50, 3, ["Put it down."]),
    (31, 2.0, 0.50, 2, ["Look up."]),
    (149, 0.6, 0.50, 2, ["Call your", "friends."]),
    (16, 7.0, 0.50, 2, ["Go", "somewhere."]),
    (63, 6.0, 0.50, 2, ["Get", "lost."]),
    (126, 1.2, 0.50, 2, ["Feel", "something."]),
    (165, 7.0, 0.50, 1, []),          # --- rapid-fire, no text
    (53, 4.0, 0.50, 1, []),
    (164, 5.0, 0.42, 1, []),
    (143, 3.0, 0.50, 1, []),
    (74, 3.2, 0.50, 4, ["The phone", "can wait."]),
    (150, 3.0, 0.50, 6, ["Your life", "can't."]),
]

# cumulative boundaries in frames (rounded from the beat grid so cuts stay on the music)
_k = 15
BOUNDS = [fr(tk(_k))]
for _s in SHOTS:
    _k += _s[3]
    BOUNDS.append(fr(tk(_k)))
CUTS = [b / FPS for b in BOUNDS[:-1]]
END_OF_SHOTS_FRAME = BOUNDS[-1]
FADE_FRAMES = 15
TOTAL_FRAMES = END_OF_SHOTS_FRAME + FADE_FRAMES
TOTAL_SEC = TOTAL_FRAMES / FPS

LOW_PCT = 100.0 * LIVING / TOTAL_WEEKS                      # 13.75 %
FINAL_SHOT_START = CUTS[-1]
PHONE_SHOT_START = CUTS[-2]
FLASH_START = CUTS[6]                                       # first rapid-fire shot
FULL_TIME = FINAL_SHOT_START + 2 * E                        # battery hits 100 %

# ---------------------------------------------------------------- voice-over
# (file, onset s, tempo)  - onset = when the first spoken sound should be heard
VO = [
    ("vo11/n_hook.mp3", 0.02, 1.3, None),         # "If you're twenty, this is your whole life."
    ("vo11/1.mp3", tk(4) - 0.03, 1.0, None),    # "Gone."
    ("vo11/2.mp3", tk(6) - 0.03, 1.0, None),    # "Asleep."
    ("vo11/n_workchores.mp3", tk(8) - 0.06, 1.3, None),   # "Work and chores."
    ("vo11/n_phone10.mp3", tk(10) - 0.05, 1.2, None),     # "Ten years on your phone."
    ("vo11/n_eleven.mp3", tk(13) - 0.02, 1.15, None),     # "Eleven. Left."  ("left" lands on the drop)
    ("vo11/n_putdown.mp3", DROP + 0.04, 1.0, None),       # "Put it down."
    ("vo11/8.mp3", PHONE_SHOT_START + 0.06, 1.0, None),   # "The phone can wait."
    ("vo11/9.mp3", FINAL_SHOT_START + 0.10, 1.0, None),   # "Your life can't."
    ("vo11/n_startliving.mp3", FINAL_SHOT_START + 1.55, 1.0, None),   # "Start living."
]
CTA_AT = FINAL_SHOT_START + 1.55                      # on-screen "Start living."
