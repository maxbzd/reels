"""Single source of truth for timing + numbers (v3: numbers get time, safe zones).

Picture timeline (seconds)
    0.0 -  1.2  hook "If you're 20, this is your whole life."
    1.2 -  2.6  "80 years / 4,160 weeks"
    2.6 -  3.9  Gone          5.2 - 6.5  Work & chores
    3.9 -  5.2  Sleep         6.5 - 8.0  Screens
    8.0 -  9.8  Left to live (count ~0.6 s, then hold 1.2 s)  ->  FLASH + DROP at 9.8 s
    9.8 -17.8   six phrases cut on the beat, then the call-to-action card

Music: "Luminary" (Joel Sunny), ~67.4 BPM.  The track swells to a peak at 7.057 s;
we stretch the lead-in (atempo ~0.72) so that peak lands exactly on the flash at 9.8 s.
After the drop the track plays at normal speed, so one eighth note E = 0.4451 s.
"""

FPS = 30
E = 0.4451                       # eighth note of the track (after the drop)


def fr(t):
    return int(round(t * FPS))


DROP = 9.8                       # flash + music hit (s)
DROP_FRAME = fr(DROP)
MUSIC_DROP = 7.057               # where the swell peaks inside the original track
LEAD_TEMPO = MUSIC_DROP / DROP   # atempo for the lead-in (~0.72)

# ---------------------------------------------------------------- the maths
# Ages 0 -> 80.  One dot = one week.  (Rough numbers, shown in the footnote.)
WEEKS_PER_YEAR = 52
TOTAL_WEEKS = 80 * WEEKS_PER_YEAR               # 4160
GONE = 20 * WEEKS_PER_YEAR                      # 1040  (ages 0-20, "If you're 20")
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
FILL_DUR = 0.60                  # counting takes ~0.6 s, the rest of the block is "hold"
# key, start (s), length (s), weeks, label, years shown
_defs = [
    ("gone",       2.6, 1.3, GONE,       "ALREADY GONE",                20),
    ("sleep",      3.9, 1.3, SLEEP,      "ASLEEP",                      20),
    ("workchores", 5.2, 1.3, WORKCHORES, "WORK & CHORES",               19),
    ("screens",    6.5, 1.5, SCREENS,    "ON SCREENS  ·  4 HRS A DAY",  10),
    ("living",     8.0, 1.8, LIVING,     "LEFT TO ACTUALLY LIVE",       11),
]
STEPS = []
_off = 0
for i, (key, t0, dur, n, label, yrs) in enumerate(_defs):
    STEPS.append(dict(idx=i, key=key, t0=t0, dur=dur, n=n, label=label, years=yrs,
                      start=_off, color=COLORS[key]))
    _off += n
assert abs(STEPS[-1]["t0"] + STEPS[-1]["dur"] - DROP) < 1e-6

# ------------------------------------------------------------- intro beats
TITLE_OUT = 1.2                 # hook is on screen from the very first frame
GRID_IN = 1.05                  # dots roll in
COUNT_IN = 1.2                  # "4,160 weeks" counts up until the first block
SIGNAL_TIMES = [7.6, 8.2, 8.75, 9.3]
SIGNAL_STATES = [(0.0, "5G", 4), (SIGNAL_TIMES[0], "4G", 3), (SIGNAL_TIMES[1], "3G", 2),
                 (SIGNAL_TIMES[2], "", 1), (SIGNAL_TIMES[3], "", 0), (DROP, "No Service", 0)]
SUCKOUT = (DROP - 0.14, DROP)   # music dips just before the hit

# ------------------------------------------------------------ montage
# (clip id, source start s, horizontal crop focus 0..1, eighths, caption lines)
SHOTS = [
    (32, 3.0, 0.50, 2, ["Put it down."]),
    (31, 2.0, 0.50, 2, ["Look up."]),
    (149, 0.6, 0.50, 2, ["Call your", "friends."]),
    (16, 7.0, 0.50, 2, ["Go", "somewhere."]),
    (74, 3.2, 0.50, 3, ["The phone", "can wait."]),
    (150, 3.0, 0.50, 7, ["Your life", "can't."]),     # 4 eighths of caption + 3 of call-to-action card
]
SHOT_DIM = {1: 0.72}            # "Look up." sits on a bright sky -> darker
CTA_LINES = ["Send this to", "someone who", "never looks up."]

_E_CUM = [0]
for _s in SHOTS:
    _E_CUM.append(_E_CUM[-1] + _s[3])
BOUNDS = [fr(DROP + E * k) for k in _E_CUM]
CUTS = [b / FPS for b in BOUNDS[:-1]]
END_OF_SHOTS_FRAME = BOUNDS[-1]
FADE_FRAMES = 15
TOTAL_FRAMES = END_OF_SHOTS_FRAME + FADE_FRAMES
TOTAL_SEC = TOTAL_FRAMES / FPS

LOW_PCT = 100.0 * LIVING / TOTAL_WEEKS                      # 13.75 %
FINAL_SHOT_START = CUTS[-1]
PHONE_SHOT_START = CUTS[-2]
CTA_AT = FINAL_SHOT_START + 4 * E                           # card appears after "Your life can't."
FULL_TIME = FINAL_SHOT_START + 2 * E                        # battery hits 100 %

# ---------------------------------------------------------------- voice-over
# (file, onset s, tempo, max seconds)  onset = when the first spoken sound should be heard
VO = [
    ("vo11/n_hook.mp3", 0.02, 1.1, None),                 # "If you're twenty, this is your whole life."
    ("vo11/1.mp3", STEPS[0]["t0"] - 0.03, 1.0, None),     # "Gone."
    ("vo11/2.mp3", STEPS[1]["t0"] - 0.03, 1.0, None),     # "Asleep."
    ("vo11/n_workchores.mp3", STEPS[2]["t0"] - 0.05, 1.0, None),   # "Work and chores."
    ("vo11/n_phone10.mp3", STEPS[3]["t0"] - 0.05, 1.1, None),      # "Ten years on your phone."
    ("vo11/n_eleven.mp3", STEPS[4]["t0"] - 0.02, 1.0, None),       # "Eleven ... left."
    ("vo11/n_putdown.mp3", DROP + 0.04, 1.0, None),                # "Put it down."
    ("vo11/8.mp3", PHONE_SHOT_START + 0.06, 1.0, None),            # "The phone can wait."
    ("vo11/9.mp3", FINAL_SHOT_START + 0.10, 1.0, None),            # "Your life can't."
]
