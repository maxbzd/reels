"""Render "Life in weeks" - a 1080x1920 / 30 fps reel.

  python3 build.py                 full render  -> ../out/life_in_weeks.mp4
  python3 build.py --stills 5,9    PNG stills of the graphic intro at those seconds

Part 1 (0 -> drop):   dot-grid data-viz drawn with numpy/Pillow.
Part 2 (drop -> end): stock clips, cut on the beat, with captions and a
                      status bar whose signal is gone and battery recharges.
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import timeline as T
import audio

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "..", "out")
W, H, FPS = 1080, 1920, T.FPS

SERIF = os.path.join(ASSETS, "fonts", "InstrumentSerif-Regular.ttf")
SERIF_I = os.path.join(ASSETS, "fonts", "InstrumentSerif-Italic.ttf")
INTER = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
INTER_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
INTER_L = "/usr/share/fonts/opentype/inter/Inter-Light.otf"

WARM = (255, 244, 222)

# ------------------------------------------------------------------ helpers


def clamp01(x):
    return max(0.0, min(1.0, x))


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp01(x)
    return 0.5 * (1 - math.cos(math.pi * x))


_font_cache, _text_cache = {}, {}


def font(path, size):
    k = (path, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(path, size)
    return _font_cache[k]


def text_layer(text, path, size, color, tracking=0, shadow=False):
    """Pre-rendered anti-aliased text -> (rgb, alpha[h,w], shadow_alpha|None)."""
    key = (text, path, size, color, tracking, shadow)
    if key in _text_cache:
        return _text_cache[key]
    f = font(path, size)
    if tracking:
        w = sum(f.getlength(c) for c in text) + tracking * (len(text) - 1)
    else:
        w = f.getlength(text)
    asc, desc = f.getmetrics()
    pad = 48 if shadow else 6
    img = Image.new("L", (int(w) + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(img)
    if tracking:
        x = pad
        for c in text:
            d.text((x, pad), c, font=f, fill=255)
            x += f.getlength(c) + tracking
    else:
        d.text((pad, pad), text, font=f, fill=255)
    alpha = np.asarray(img, np.float32) / 255.0
    sh = None
    if shadow:
        s = img.filter(ImageFilter.GaussianBlur(16))
        sh = np.asarray(s, np.float32) / 255.0 * 0.85
        sh = np.roll(sh, 8, axis=0)
    out = (np.array(color, np.float32), alpha, sh)
    _text_cache[key] = out
    return out


def blit_text(frame, layer, cx, cy, opacity=1.0, dy=0):
    if opacity <= 0.003:
        return
    rgb, a, sh = layer
    h, w = a.shape
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2 + dy))
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    sl = (slice(ya, yb), slice(xa, xb))
    sub = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    if sh is not None:
        frame[sl] *= (1 - sh[sub] * opacity)[..., None]
    al = (a[sub] * opacity)[..., None]
    frame[sl] = frame[sl] * (1 - al) + rgb * al


# ------------------------------------------------------------ status icons
_icon_cache = {}
SS = 3  # supersample


def _layer_to_arr(img):
    a = np.asarray(img, np.float32)
    return a[..., :3], a[..., 3] / 255.0


def battery_icon(pct, charging, tone):
    """tone: 'white' | 'red' | 'green'"""
    key = ("bat", int(round(pct)), charging, tone)
    if key in _icon_cache:
        return _icon_cache[key]
    col = {"white": (255, 255, 255), "red": (255, 69, 58), "green": (80, 235, 120)}[tone]
    bw, bh = 92, 44
    label_font = font(INTER_SB, 34)
    label = f"{int(round(pct))}%"
    lw = label_font.getlength(label)
    gap = 14
    tw = int(lw + gap + bw + 12 + 8)
    th = 64
    img = Image.new("RGBA", (tw * SS, th * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    big = font(INTER_SB, 34 * SS)
    d.text((0, th * SS / 2), label, font=big, fill=col + (255,), anchor="lm")
    bx = int((lw + gap) * SS)
    by = int((th - bh) / 2 * SS)
    d.rounded_rectangle((bx, by, bx + bw * SS, by + bh * SS), radius=12 * SS,
                        outline=col + (170,), width=3 * SS)
    d.rounded_rectangle((bx + bw * SS + 4 * SS, by + 14 * SS, bx + bw * SS + 9 * SS, by + 30 * SS),
                        radius=2 * SS, fill=col + (170,))
    inner = bw - 10
    fw = max(0.0, inner * pct / 100.0)
    if fw > 0:
        d.rounded_rectangle((bx + 5 * SS, by + 5 * SS, bx + (5 + fw) * SS, by + (bh - 5) * SS),
                            radius=8 * SS if fw > 16 else 3 * SS, fill=col + (255,))
    if charging:
        cx, cy = bx + bw * SS / 2, by + bh * SS / 2
        s = SS * 1.0
        poly = [(cx + 3 * s, cy - 15 * s), (cx - 9 * s, cy + 3 * s), (cx - 1 * s, cy + 3 * s),
                (cx - 4 * s, cy + 16 * s), (cx + 9 * s, cy - 3 * s), (cx + 1 * s, cy - 3 * s)]
        d.polygon(poly, fill=(10, 10, 14, 235), outline=(255, 255, 255, 255))
    img = img.resize((tw, th), Image.LANCZOS)
    out = _layer_to_arr(img)
    _icon_cache[key] = out
    return out


def signal_icon(bars, label):
    key = ("sig", bars, label)
    if key in _icon_cache:
        return _icon_cache[key]
    heights, bwid, gap = [12, 20, 28, 36], 9, 5
    lab_font = font(INTER_SB, 34)
    lw = lab_font.getlength(label) if label else 0
    tw = int(4 * bwid + 3 * gap + (16 + lw if label else 0) + 6)
    th = 64
    img = Image.new("RGBA", (tw * SS, th * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = (th + 36) / 2
    for i, hh in enumerate(heights):
        x = i * (bwid + gap)
        on = i < bars
        d.rounded_rectangle((x * SS, (base - hh) * SS, (x + bwid) * SS, base * SS), radius=2.5 * SS,
                            fill=(255, 255, 255, 255 if on else 70))
    if label:
        d.text(((4 * bwid + 3 * gap + 16) * SS, th * SS / 2), label, font=font(INTER_SB, 34 * SS),
               fill=(255, 255, 255, 255), anchor="lm")
    img = img.resize((tw, th), Image.LANCZOS)
    out = _layer_to_arr(img)
    _icon_cache[key] = out
    return out


def blit_arr(frame, arr, x, y, opacity=1.0, anchor="l"):
    rgb, a = arr
    h, w = a.shape
    x0 = int(x if anchor == "l" else x - w)
    y0 = int(y - h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    sl = (slice(ya, yb), slice(xa, xb))
    sub = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    al = (a[sub] * opacity)[..., None]
    frame[sl] = frame[sl] * (1 - al) + rgb[sub] * al


STATUS_Y = 297


def status_bar(frame, t, pct, charging):
    # signal / network (left)
    label, bars = "5G", 4
    for ts, lab, b in T.SIGNAL_STATES:
        if t >= ts - 1e-6:
            label, bars = lab, b
    blit_arr(frame, signal_icon(bars, label), 84, STATUS_Y, 1.0, "l")
    # battery (right)
    if charging:
        tone = "green"
    elif pct <= 20:
        tone = "red"
    else:
        tone = "white"
    blit_arr(frame, battery_icon(pct, charging, tone), W - 84, STATUS_Y, 1.0, "r")


# --------------------------------------------------------------------- grid
# Instagram safe zones (1080x1920): keep everything between y=270 and y=1250, x>=65,
# and keep anything important left of ~900 px (right-hand buttons).
COLS, ROWS = 52, 80
PX, PY = 11, 9                 # cell size; dots are slightly flattened ovals
GX0 = 158
GY0 = 492                      # grid spans y 492 .. 1212
UNLIT = np.array([34, 35, 46], np.float32)
TOP_LABEL_Y, TOP_NUM_Y, FOOT_Y = 352, 438, 1238


def _make_sprite():
    rx, ry = 4.1, 3.3
    cx, cy = (PX - 1) / 2.0, (PY - 1) / 2.0
    yy, xx = np.mgrid[0:PY, 0:PX].astype(np.float32)
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    return np.clip((1 - d) * min(rx, ry) + 0.5, 0, 1).astype(np.float32)


SPRITE = _make_sprite()
COVER = float(SPRITE.sum()) / (PX * PY)         # share of a cell that a dot covers
_ROW = (np.arange(T.TOTAL_WEEKS) // COLS).astype(np.float32)
_COL = (np.arange(T.TOTAL_WEEKS) % COLS).astype(np.float32)
_IDX = np.arange(T.TOTAL_WEEKS)


def light(c, k=0.35):
    """blend a colour towards white (small text must read on black)"""
    return tuple(int(v + (255 - v) * k) for v in c)


def lit_counts(t):
    """weeks lit per step at time t (int list)"""
    out = []
    for s in T.STEPS:
        p = ease_io((t - s["t0"] - T.FILL_DELAY) / T.FILL_DUR)
        out.append(int(round(p * s["n"])))
    return out


def grid_image(t, dim):
    n = T.TOTAL_WEEKS
    lit = np.zeros((n, 3), np.float32)
    mask = np.zeros(n, np.float32)
    flash = np.zeros(n, np.float32)
    counts = lit_counts(t)
    for s, k in zip(T.STEPS, counts):
        if k <= 0:
            continue
        sl = slice(s["start"], s["start"] + k)
        col = np.array(s["color"], np.float32)
        lit[sl] = col
        mask[sl] = 1.0
        age = (k - 1 - np.arange(k)).astype(np.float32)
        done_t = s["t0"] + T.FILL_DELAY + T.FILL_DUR
        age = age + max(0.0, t - done_t) * 900.0
        flash[sl] = np.clip(1 - age / 90.0, 0, 1)
        if s["key"] == "living" and t > done_t:
            pulse = 1.0 + 0.22 * math.sin(2 * math.pi * (t - done_t) / 1.2)
            lit[sl] = np.clip(col * pulse, 0, 255)
    lit = lit + flash[:, None] * (255 - lit) * 0.55 * mask[:, None]

    appear = np.clip((t - T.GRID_IN - _ROW * 0.005 - _COL * 0.002) / 0.25, 0, 1)
    base = np.where(mask[:, None] > 0, lit, UNLIT[None, :]) * appear[:, None]
    glow_src = lit * mask[:, None] * appear[:, None]

    # tile the dots
    base = base.reshape(ROWS, COLS, 3)
    tiles = base[:, :, None, None, :] * SPRITE[None, None, :, :, None]
    img = tiles.transpose(0, 2, 1, 3, 4).reshape(ROWS * PY, COLS * PX, 3)

    # glow (computed from the lit dots only, at low resolution)
    g = (glow_src * COVER).reshape(ROWS, COLS, 3).astype(np.uint8)
    gi = Image.fromarray(g).resize((COLS * 2, ROWS * 2), Image.NEAREST)
    g1 = gi.filter(ImageFilter.GaussianBlur(2.0)).resize((COLS * PX, ROWS * PY), Image.BICUBIC)
    g2 = gi.filter(ImageFilter.GaussianBlur(6.5)).resize((COLS * PX, ROWS * PY), Image.BICUBIC)
    img = img + np.asarray(g1, np.float32) * 0.9 + np.asarray(g2, np.float32) * 1.6
    return np.clip(img * dim, 0, 255)


# ---------------------------------------------------------------- intro frame


def fade(t, t0, dur=0.3, t1=None, dur_out=0.2):
    a = smooth((t - t0) / dur)
    if t1 is not None:
        a *= 1 - smooth((t - t1) / dur_out)
    return a


_EDGE = None


def edge_mask():
    global _EDGE
    if _EDGE is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _EDGE = np.clip((d - 0.35) / 0.85, 0, 1) ** 1.6
    return _EDGE


def camera(frame, t):
    """punch-zooms on every block, shake during the SCREENS block, creeping zoom into the drop"""
    z, dx, dy = 1.0, 0.0, 0.0
    for s in T.STEPS:
        dt = t - s["t0"]
        if 0 <= dt < 0.4:
            z += 0.05 * math.exp(-dt / 0.09)
    sc = T.STEPS[3]
    if sc["t0"] <= t < sc["t0"] + sc["dur"]:
        a = 9 * (1 - (t - sc["t0"]) / sc["dur"])
        dx, dy = a * math.sin(t * 95), a * math.cos(t * 83)
        z += 0.03
    lv = T.STEPS[4]
    if t >= lv["t0"]:
        z += 0.07 * smooth((t - lv["t0"]) / lv["dur"])
    if t < 0.3:
        z += 0.10 * (1 - t / 0.3) ** 2
    if z == 1.0 and dx == 0 and dy == 0:
        return frame
    ww, hh = W / z, H / z
    x0, y0 = (W - ww) / 2 - dx, (H - hh) / 2 - dy
    x0, y0 = max(0.0, min(W - ww, x0)), max(0.0, min(H - hh, y0))
    im = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).resize(
        (W, H), Image.BILINEAR, box=(x0, y0, x0 + ww, y0 + hh))
    return np.asarray(im, np.float32)


LEGEND_MAX_X = 900            # nothing right of this: Instagram's like/comment/share column


def side_labels(frame, t):
    """name + bracket right of each block (kept left of 900 px), years on the left"""
    names = {"gone": ["Gone"], "sleep": ["Sleep"], "workchores": ["Work &", "chores"],
             "screens": ["Screens"], "living": ["Left to", "live"]}
    xr = GX0 + COLS * PX
    for s in T.STEPS:
        if t < s["t0"] or t >= T.DROP:
            continue
        p = ease_io((t - s["t0"] - T.FILL_DELAY) / T.FILL_DUR)
        a = fade(t, s["t0"], 0.10)
        r0 = s["start"] / COLS
        r1 = (s["start"] + s["n"]) / COLS
        y0 = GY0 + r0 * PY
        y1 = GY0 + (r0 + (r1 - r0) * max(p, 0.02)) * PY
        xb = xr + 12
        ya, yb = int(y0 + 2), int(max(y0 + 6, y1 - 2))
        col = np.array(s["color"], np.float32)
        reg = frame[ya:yb, xb:xb + 3]
        frame[ya:yb, xb:xb + 3] = reg * (1 - 0.9 * a) + col * 0.9 * a
        yc = (y0 + y1) / 2
        lines = names[s["key"]]
        for i, line in enumerate(lines):
            lay = text_layer(line, INTER_SB, 34, light(s["color"], 0.25))
            w = lay[1].shape[1] - 12
            assert xb + 18 + w <= LEGEND_MAX_X, (line, xb + 18 + w)
            dy = (i - (len(lines) - 1) / 2) * 40
            blit_text(frame, lay, xb + 18 + w / 2, yc + dy, a)
        yrs = int(round(p * s["years"]))
        lay = text_layer(f"{yrs}y", INTER_SB, 38, light(s["color"], 0.25))
        w = lay[1].shape[1] - 12
        blit_text(frame, lay, GX0 - 14 - w / 2, yc, a)


def render_intro(f):
    t = f / FPS
    frame = np.zeros((H, W, 3), np.float32)

    # --- hook: on screen from the first frames
    if t < T.TITLE_OUT + 0.3:
        a1 = fade(t, 0.0, 0.09, T.TITLE_OUT - 0.08, 0.18)
        blit_text(frame, text_layer("If you're 20,", SERIF, 200, (255, 255, 255)), W / 2, 800, a1,
                  dy=(1 - ease_out(t / 0.28)) * 46)
        a2 = fade(t, 0.25, 0.2, T.TITLE_OUT - 0.08, 0.18)
        blit_text(frame, text_layer("this is your whole life.", INTER_L, 52, (215, 218, 228)),
                  W / 2, 970, a2)

    # --- grid
    if t >= T.GRID_IN:
        frame[GY0:GY0 + ROWS * PY, GX0:GX0 + COLS * PX] = grid_image(t, 1.0)

    side_labels(frame, t)

    # --- caption block above the grid
    step = None
    for s in T.STEPS:
        if t >= s["t0"]:
            step = s
    if T.COUNT_IN <= t < T.DROP:
        if step is None:  # "80 years / 4,160 weeks"
            p = ease_out((t - T.COUNT_IN) / 0.9)
            a = fade(t, T.COUNT_IN, 0.1)
            blit_text(frame, text_layer("80 YEARS", INTER_SB, 36, (205, 209, 220), tracking=7), W / 2, TOP_LABEL_Y, a)
            blit_text(frame, text_layer(f"{int(round(p * T.TOTAL_WEEKS)):,} weeks", SERIF, 112, (255, 255, 255)),
                      W / 2, TOP_NUM_Y, a)
        else:
            p = ease_io((t - step["t0"] - T.FILL_DELAY) / T.FILL_DUR)
            a = fade(t, step["t0"], 0.07)
            yrs = int(round(p * step["years"]))
            blit_text(frame, text_layer(step["label"], INTER_SB, 36, light(step["color"], 0.3), tracking=7),
                      W / 2, TOP_LABEL_Y, a)
            unit = "year" if yrs == 1 else "years"
            blit_text(frame, text_layer(f"{yrs} {unit}", SERIF, 112, (255, 255, 255)), W / 2, TOP_NUM_Y, a)
        blit_text(frame, text_layer("1 dot = 1 week  ·  ages 0 – 80  ·  rough estimate", INTER, 30,
                                    (200, 204, 216)), W / 2, FOOT_Y, fade(t, T.COUNT_IN + 0.3, 0.3))

    # --- status bar: battery drains with the "life" being used up
    counts = lit_counts(t)
    pct = 100.0 * (1 - sum(counts[:4]) / T.TOTAL_WEEKS)
    status_bar(frame, t, pct, charging=False)

    # --- camera + alarm flash on the SCREENS block
    frame = camera(frame, t)
    sc = T.STEPS[3]
    dt = t - sc["t0"]
    if 0 <= dt < 0.5:
        frame[..., 0] += 110 * math.exp(-dt / 0.18) * edge_mask()
    # split-second dip to black right before the drop (the music is sucked out too)
    if T.SUCKOUT[0] <= t < T.SUCKOUT[1]:
        frame *= 0.10
    return np.clip(frame, 0, 255).astype(np.uint8)


def render_cover(path):
    """profile-grid cover: the filled grid with '11 years' in the centre square"""
    frame = np.zeros((H, W, 3), np.float32)
    gx = (W - COLS * PX) // 2
    gy = 520
    g = grid_image(T.DROP - 0.3, 0.55)
    frame[gy:gy + ROWS * PY, gx:gx + COLS * PX] = g
    # darken behind the text
    yy = np.arange(H, dtype=np.float32)
    band = (0.62 * np.exp(-((yy - 860) / 230) ** 2))[:, None, None]
    frame *= (1 - band)
    green = (120, 255, 175)
    blit_text(frame, text_layer("LEFT TO ACTUALLY LIVE", INTER_SB, 44, green, tracking=9), W / 2, 700, 1.0)
    blit_text(frame, text_layer("11 years", SERIF, 270, (255, 255, 255), shadow=True), W / 2, 860, 1.0)
    blit_text(frame, text_layer("out of your 80", INTER, 48, (225, 228, 238)), W / 2, 1030, 1.0)
    Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).save(path)


# ---------------------------------------------------------------- clip part
_VIG_BOTTOM = None


def vignette():
    global _VIG_BOTTOM
    if _VIG_BOTTOM is None:
        y = np.linspace(0, 1, H, dtype=np.float32)
        bottom = np.clip((y - 0.55) / 0.45, 0, 1) ** 1.5 * 0.45
        top = np.clip(1 - y / 0.18, 0, 1) ** 1.5 * 0.40
        base = 1 - np.maximum(bottom, top)
        band = 0.30 * np.exp(-(((y * H) - 1100) / 230) ** 2)        # soft shade behind the captions
        _VIG_BOTTOM = (base * (1 - band))[:, None, None].astype(np.float32)
    return _VIG_BOTTOM


SRC_W, SRC_H = W, H


def decode(clip, ss, n_frames, cx):
    path = os.path.join(ASSETS, "clips", f"{clip}.mp4")
    vf = (f"scale=-2:{SRC_H}:flags=lanczos,crop={SRC_W}:{SRC_H}:(iw-{SRC_W})*{cx}:0,"
          f"fps={FPS},eq=contrast=1.08:saturation=1.14:gamma=0.97,unsharp=5:5:0.6")
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{ss}", "-i", path, "-vf", vf, "-frames:v", str(n_frames),
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = SRC_W * SRC_H * 3
    for _ in range(n_frames):
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(SRC_H, SRC_W, 3)
    p.stdout.close()
    p.wait()


rng = np.random.default_rng(11)


def render_clips():
    vig = vignette()
    last_i = len(T.SHOTS) - 1
    for si, (clip, ss, cx, eighths, lines) in enumerate(T.SHOTS):
        f0 = T.BOUNDS[si]
        n = T.BOUNDS[si + 1] - f0
        if si == last_i:
            n += T.FADE_FRAMES              # last shot carries the fade-out
        last, done = None, 0
        for j, src in enumerate(decode(clip, ss, n, cx)):
            last = src
            done = j + 1
            yield f0 + j, compose_clip(src, si, j, n, f0 + j, vig, lines)
        for j in range(done, n):            # source ended early -> hold last frame
            yield f0 + j, compose_clip(last, si, j, n, f0 + j, vig, lines)


def blit_text_scaled(frame, layer, cx, cy, opacity, scale, dy=0):
    if abs(scale - 1.0) < 0.01:
        return blit_text(frame, layer, cx, cy, opacity, dy)
    rgb, a, sh = layer
    h, w = a.shape
    size = (max(1, int(w * scale)), max(1, int(h * scale)))
    a2 = np.asarray(Image.fromarray(a).resize(size, Image.BILINEAR), np.float32)
    sh2 = None if sh is None else np.asarray(Image.fromarray(sh).resize(size, Image.BILINEAR), np.float32)
    blit_text(frame, (rgb, a2, sh2), cx, cy, opacity, dy)


CAP_Y1, CAP_Y2 = 1130, (1040, 1168)       # caption rows (inside the 270..1250 safe band)
CTA_Y = (880, 1010, 1140)


def compose_clip(src, si, j, n, fg, vig, lines):
    t = fg / FPS
    prog = j / max(1, n - 1)
    last_shot = si == len(T.SHOTS) - 1
    # punch-in on the beat that relaxes into a slow push
    z = 1.0 + (0.20 if si == 0 else 0.13) * math.exp(-j / 3.2) + 0.07 * prog
    ww, hh = W / z, H / z
    x0, y0 = (W - ww) / 2, (H - hh) / 2
    im = Image.fromarray(src).resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + ww, y0 + hh))
    frame = np.asarray(im, np.float32) * vig * T.SHOT_DIM.get(si, 1.0)

    # call-to-action card: the last shot is dimmed and the caption hands over to the card
    cj = int(round((T.CTA_AT - T.CUTS[-1]) * FPS))
    ca = smooth((j - cj) / 7.0) if last_shot else 0.0
    if ca > 0:
        frame *= 1 - 0.58 * ca

    # chromatic split on the first frames of every cut
    if j < 4:
        sh = int(14 * (1 - j / 4))
        if sh:
            frame[..., 0] = np.roll(frame[..., 0], sh, axis=1)
            frame[..., 2] = np.roll(frame[..., 2], -sh, axis=1)

    # captions: pop in with overshoot
    col = (255, 255, 255) if last_shot else WARM
    ys = [CAP_Y1] if len(lines) == 1 else list(CAP_Y2)
    for li, line in enumerate(lines):
        d0 = 1 + li * 3
        a = smooth((j - d0) / 3.0) * (1 - ca)
        p = clamp01((j - d0) / 9.0)
        scale = 1.0 + 0.45 * (1 - ease_out(p)) ** 1.5
        path = SERIF_I if (li == len(lines) - 1 and len(lines) > 1) else SERIF
        blit_text_scaled(frame, text_layer(line, path, 140, col, shadow=True), W / 2, ys[li], a, scale)

    if ca > 0:
        for li, line in enumerate(T.CTA_LINES):
            d = clamp01((ca * 7 - li * 1.2) / 6.0)
            path = SERIF_I if li == len(T.CTA_LINES) - 1 else SERIF
            lay = text_layer(line, path, 112, (255, 236, 200) if li == len(T.CTA_LINES) - 1 else (255, 255, 255),
                             shadow=True)
            assert lay[1].shape[1] - 96 <= 780, (line, lay[1].shape[1])
            blit_text(frame, lay, W / 2 - 40, CTA_Y[li], smooth(d), dy=(1 - ease_out(d)) * 30)

    # white flash on the beat
    if si == 0:
        fl = 0.95 * max(0.0, 1 - j / 9.0) ** 1.4
    else:
        fl = 0.60 * max(0.0, 1 - j / 5.0) ** 1.5
    if fl > 0:
        frame = frame + (255 - frame) * fl

    # status bar: no signal, battery recharging (stays on the CTA card: 100 %)
    p = smooth((t - T.DROP) / (T.FULL_TIME - T.DROP))
    pct = T.LOW_PCT + (100 - T.LOW_PCT) * p
    status_bar(frame, t, pct, charging=pct < 99.5)

    # film grain
    frame += rng.standard_normal((H, W, 1), dtype=np.float32) * 1.8

    # fade to black at the very end
    if last_shot:
        fade_start = n - T.FADE_FRAMES
        if j >= fade_start:
            frame *= 1 - (j - fade_start + 1) / T.FADE_FRAMES
    return np.clip(frame, 0, 255).astype(np.uint8)


def mux(video, wav, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{T.TOTAL_SEC:.3f}", "-movflags", "+faststart", out], check=True)


def render_video(path):
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-maxrate", "14M", "-bufsize", "28M",
         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-an", path],
        stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, fr in enumerate(pool.imap(render_intro, range(T.DROP_FRAME), chunksize=4)):
            enc.stdin.write(fr.tobytes())
    last = None
    for fg, fr in render_clips():
        enc.stdin.write(fr.tobytes())
        last = fg
    assert last == T.TOTAL_FRAMES - 1, (last, T.TOTAL_FRAMES)
    enc.stdin.close()
    enc.wait()


def main():
    os.makedirs(OUT, exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[1] == "--stills":
        d = os.path.join(OUT, "stills")
        os.makedirs(d, exist_ok=True)
        for tt in sys.argv[2].split(","):
            f = int(round(float(tt) * FPS))
            Image.fromarray(render_intro(f)).save(os.path.join(d, f"intro_{float(tt):05.2f}.png"))
            print("saved", tt)
        return

    if "--cover" in sys.argv:
        render_cover(os.path.join(OUT, "cover.png"))
        print("cover saved")
        return

    video = os.path.join(OUT, "_video.mp4")
    if "--audio-only" not in sys.argv:
        render_video(video)
        print("video rendered", flush=True)
    wav = os.path.join(OUT, "_mix.wav")
    audio.build_mix(wav, with_music=True)
    mux(video, wav, os.path.join(OUT, "life_in_weeks.mp4"))
    wav2 = os.path.join(OUT, "_mix_nomusic.wav")
    audio.build_mix(wav2, with_music=False)
    mux(video, wav2, os.path.join(OUT, "life_in_weeks_no_music.mp4"))
    print("done")


if __name__ == "__main__":
    main()
