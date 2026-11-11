"""Single source of truth for timing + numbers. Everything is locked to the
music's beat grid: track "Drawing the Sky" is 100 BPM (0.6 s/beat) with the
drop at 14.82 s.  30 fps => one beat = exactly 18 frames.
"""

FPS = 30
BEAT = 0.6
DROP = 14.82                     # the drop in the track, seconds
DROP_FRAME = round(DROP * FPS)   # 445

# ---------------------------------------------------------------- the maths
# Ages 20 -> 80.  One dot = one week.  (Rough numbers, shown in the footnote.)
WEEKS_PER_YEAR = 52
TOTAL_WEEKS = 80 * WEEKS_PER_YEAR               # 4160
GONE = 20 * WEEKS_PER_YEAR                      # 1040  (ages 0-20)
REMAINING = TOTAL_WEEKS - GONE                  # 3120  (60 years)
SLEEP = REMAINING // 3                          # 1040  (8 h/day = 1/3)
WORK = 9 * WEEKS_PER_YEAR                       # 468   (~9 years of work/school)
CHORES = 10 * WEEKS_PER_YEAR                    # 520   (chores, commuting, hygiene)
SCREENS = REMAINING // 6                        # 520   (4 h/day = 1/6 of a day)
LIVING = REMAINING - SLEEP - WORK - CHORES - SCREENS   # 572 weeks = 11 years
assert LIVING == 572 and GONE + SLEEP + WORK + CHORES + SCREENS + LIVING == TOTAL_WEEKS

COLORS = {
    "gone": (118, 124, 140),
    "sleep": (140, 100, 255),
    "work": (255, 70, 160),
    "chores": (40, 210, 240),
    "screens": (255, 110, 50),
    "living": (90, 255, 160),
}

# t0 = start of the step (on a beat), n = weeks, years shown as big number
FILL_DELAY = 0.10
FILL_DUR = 0.95
_defs = [
    ("gone",    4.02, GONE,    "ALREADY GONE",             20),
    ("sleep",   5.22, SLEEP,   "ASLEEP",                   20),
    ("work",    6.42, WORK,    "AT WORK & SCHOOL",          9),
    ("chores",  7.62, CHORES,  "CHORES & COMMUTING",       10),
    ("screens", 8.82, SCREENS, "ON SCREENS  ·  4 HRS A DAY", 10),
    ("living", 10.62, LIVING,  "LEFT TO ACTUALLY LIVE",    11),
]
STEPS = []
_off = 0
for i, (key, t0, n, label, yrs) in enumerate(_defs):
    STEPS.append(dict(idx=i, key=key, t0=t0, n=n, label=label, years=yrs,
                      start=_off, color=COLORS[key]))
    _off += n

# ------------------------------------------------------------- intro beats
TITLE_IN = 0.42                 # "You're 20."
SUB_IN = 1.62                   # "Your whole life, in weeks."
GRID_IN = 2.22                  # dots roll in
COUNT_IN = 2.82                 # "4,160 weeks"
RISER_START = 12.42
DISCONNECT_IN = 12.60           # "What if you"
DISCONNECT2_IN = 13.62          # "disconnected?"

# signal bars degrade on the 4 beats before the drop
SIGNAL_TIMES = [DROP - 0.6 * k for k in (4, 3, 2, 1)]      # 12.42, 13.02, 13.62, 14.22
# state: (label, bars) valid from that time
SIGNAL_STATES = [(0.0, "5G", 4), (SIGNAL_TIMES[0], "4G", 3), (SIGNAL_TIMES[1], "3G", 2),
                 (SIGNAL_TIMES[2], "", 1), (SIGNAL_TIMES[3], "", 0), (DROP, "No Service", 0)]

# ------------------------------------------------------------ nature section
# (clip id, source start s, horizontal crop focus 0..1, beats, caption lines)
SHOTS = [
    (32, 3.0, 0.50, 2, ["Put it down."]),
    (31, 2.0, 0.50, 2, ["Look up."]),
    (149, 0.6, 0.50, 2, ["Call your", "friends."]),
    (16, 7.0, 0.50, 2, ["Go", "somewhere."]),
    (63, 6.0, 0.50, 2, ["Get a little", "lost."]),
    (126, 1.2, 0.50, 2, ["Feel", "something."]),
    (74, 3.2, 0.50, 4, ["The phone", "can wait."]),
    (150, 3.0, 0.50, 4, ["Your life", "can't."]),
]
CUTS = []
_f = DROP_FRAME
for _s in SHOTS:
    CUTS.append(_f / FPS)
    _f += _s[3] * 18
END_OF_SHOTS_FRAME = _f                                    # 805 (last shot then fades out)
FADE_FRAMES = 27
TOTAL_FRAMES = END_OF_SHOTS_FRAME + FADE_FRAMES
TOTAL_SEC = TOTAL_FRAMES / FPS

LOW_PCT = 100.0 * LIVING / TOTAL_WEEKS                      # 13.75 %
FULL_TIME = CUTS[-1] + 2 * BEAT                                # battery hits 100 %  (25.62)
