"""Render 'The breakup' - a 1080x1920 / 30 fps chat reel.

    python3 render.py                 full render -> ../out/breakup.mp4 (+ _no_music)
    python3 render.py --stills 1,5    PNG stills at those seconds
    python3 render.py --audio-only    re-mix sound only
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import script as S

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
W, H, FPS = 1080, 1920, S.FPS

FONTS = os.path.join(HERE, "..", "life_in_weeks", "assets", "fonts")
SERIF = os.path.join(FONTS, "InstrumentSerif-Regular.ttf")
SERIF_I = os.path.join(FONTS, "InstrumentSerif-Italic.ttf")
INTER_M = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
INTER_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
INTER_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
INTER_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"

IG_BUBBLE = (38, 38, 43)
ME_BUBBLE = (10, 132, 255)
GRAY = (142, 142, 147)
RED = (255, 69, 58)
BLUE = (10, 132, 255)

# --------------------------------------------------------------- helpers


def clamp01(x):
    return max(0.0, min(1.0, x))


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    return 0.5 * (1 - math.cos(math.pi * clamp01(x)))


def ease_back(x, s=1.9):
    x = clamp01(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


_fonts = {}


def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]


_tcache = {}


def text_arr(text, path, size, color, tracking=0):
    """anti-aliased text -> (rgb(3,), alpha[h,w]) ; drawn at 2x and downsampled"""
    key = (text, path, size, color, tracking)
    if key in _tcache:
        return _tcache[key]
    SS = 2
    f = font(path, size * SS)
    w = sum(f.getlength(c) for c in text) + tracking * SS * (len(text) - 1) if tracking else f.getlength(text)
    asc, desc = f.getmetrics()
    pad = 8 * SS
    img = Image.new("L", (int(w) + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(img)
    if tracking:
        x = pad
        for c in text:
            d.text((x, pad), c, font=f, fill=255)
            x += f.getlength(c) + tracking * SS
    else:
        d.text((pad, pad), text, font=f, fill=255)
    img = img.resize((img.width // SS, img.height // SS), Image.LANCZOS)
    out = (np.array(color, np.float32), np.asarray(img, np.float32) / 255.0)
    _tcache[key] = out
    return out


def blit(frame, layer, cx, cy, opacity=1.0, anchor="c", scale=1.0):
    """layer = (rgb(3,) | rgb(h,w,3), alpha(h,w)); anchor: c / l / r (horizontal) at cy centre"""
    rgb, a = layer
    if opacity <= 0.003:
        return
    if abs(scale - 1.0) > 0.01:
        h0, w0 = a.shape
        size = (max(1, int(w0 * scale)), max(1, int(h0 * scale)))
        a = np.asarray(Image.fromarray(a).resize(size, Image.BILINEAR), np.float32)
        if rgb.ndim == 3:
            rgb = np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize(size, Image.BILINEAR), np.float32)
    h, w = a.shape
    x0 = int(round(cx - w / 2)) if anchor == "c" else (int(round(cx)) if anchor == "l" else int(round(cx - w)))
    y0 = int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    sub = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    al = (a[sub] * opacity)[..., None]
    col = rgb if rgb.ndim == 1 else rgb[sub]
    frame[ya:yb, xa:xb] = frame[ya:yb, xa:xb] * (1 - al) + col * al


def blit_bottom(frame, layer, x, bottom, opacity=1.0, scale=1.0, origin="l"):
    """place a bubble layer with its bottom edge at `bottom`, scaled around the outer-bottom corner"""
    rgb, a = layer
    if opacity <= 0.003:
        return
    h0, w0 = a.shape
    if abs(scale - 1.0) > 0.01:
        size = (max(1, int(w0 * scale)), max(1, int(h0 * scale)))
        a = np.asarray(Image.fromarray(a).resize(size, Image.BILINEAR), np.float32)
        rgb = np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize(size, Image.BILINEAR), np.float32)
    h, w = a.shape
    x0 = int(round(x)) if origin == "l" else int(round(x - w))
    y0 = int(round(bottom - h))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    sub = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    al = (a[sub] * opacity)[..., None]
    frame[ya:yb, xa:xb] = frame[ya:yb, xa:xb] * (1 - al) + rgb[sub] * al


def rr_layer(w, h, radius, fill, outline=None, ow=3, SS=2):
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), radius=radius * SS, fill=fill + (255,),
                        outline=(outline + (255,)) if outline else None, width=ow * SS)
    img = img.resize((w, h), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    return arr[..., :3], arr[..., 3] / 255.0


# ----------------------------------------------------------------- bubbles
PADX, PADY, LINEH, BUB_MAXW = 36, 24, 56, 660
CHAT_L, CHAT_R = 70, 905           # left edge of IG bubbles / right edge of your bubbles (kept left of 910 px)
VIEW_BOTTOM = 1105
GAP_SAME, GAP_DIFF = 12, 28
TYPING_H = 96
_bub = {}


def wrap(text, f, maxw):
    words, lines, cur = text.split(" "), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if f.getlength(t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    return lines


def bubble(text, side):
    key = (text, side)
    if key in _bub:
        return _bub[key]
    SS = 2
    f = font(INTER_M, 44 * SS)
    lines = wrap(text, font(INTER_M, 44), BUB_MAXW - 2 * PADX)
    lw = max(font(INTER_M, 44).getlength(l) for l in lines)
    w, h = int(lw + 2 * PADX), int(len(lines) * LINEH + 2 * PADY)
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fill = {"me": ME_BUBBLE, "ig": IG_BUBBLE, "fail": (58, 26, 28)}[side]
    d.rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), radius=min(52, h // 2) * SS, fill=fill + (255,),
                        outline=(RED + (255,)) if side == "fail" else None, width=3 * SS)
    for i, l in enumerate(lines):
        d.text((PADX * SS, (PADY + i * LINEH - 2) * SS), l, font=f, fill=(255, 255, 255, 255))
    img = img.resize((w, h), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    out = (arr[..., :3], arr[..., 3] / 255.0)
    _bub[key] = out
    return out


_typ = {}


def typing_bubble(phase):
    k = int(phase * 12) % 12
    if k in _typ:
        return _typ[k]
    SS, w, h = 2, 150, TYPING_H
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), radius=48 * SS, fill=IG_BUBBLE + (255,))
    for i in range(3):
        ph = (k / 12.0 - i * 0.16) % 1.0
        lift = max(0.0, math.sin(ph * math.pi * 2)) * 8
        a = 120 + int(100 * max(0.0, math.sin(ph * math.pi * 2)))
        cx, cy = (38 + i * 37) * SS, (h / 2 - lift) * SS
        r = 9 * SS
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(200, 200, 205, a))
    img = img.resize((w, h), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    _typ[k] = (arr[..., :3], arr[..., 3] / 255.0)
    return _typ[k]


# ----------------------------------------------------------------- layout
def _gaps():
    prev = None
    out = []
    for m in S.MSGS:
        if m["side"] == "ts":
            out.append(30 if prev is not None else 0)
        elif prev is None:
            out.append(10)
        else:
            out.append(GAP_SAME if prev == m["side"] or (prev, m["side"]) == ("ig", "fail") else GAP_DIFF)
        prev = m["side"] if m["side"] != "ts" else None
    return out


GAPS = _gaps()
FAIL_LABEL_H = 54


def bub_h(m):
    if m["side"] == "ts":
        return 44
    return bubble(m["text"], "ig" if m["side"] == "ig" else m["side"])[1].shape[0]


def slot_h(m, gap, t):
    """animated height of a message slot (gap above + bubble [+ label])"""
    show = m["show"]
    extra = FAIL_LABEL_H if m["side"] == "fail" else 0
    final = gap + bub_h(m) + extra
    ts = m.get("type_start")
    if m["side"] in ("ig", "fail"):
        if t < ts:
            return 0.0
        if t < show:
            return (gap + TYPING_H) * smooth((t - ts) / 0.25)
        return (gap + TYPING_H) + (final - gap - TYPING_H) * smooth((t - show) / 0.22)
    if t < show:
        return 0.0
    return final * smooth((t - show) / 0.28)


VIEW_TOP = 350


def draw_chat(layer, t):
    """bubbles stack from the top like a real chat and scroll only once they no longer fit"""
    slots = [slot_h(m, g, t) for m, g in zip(S.MSGS, GAPS)]
    total = sum(slots)
    shift = max(0.0, total - (VIEW_BOTTOM - VIEW_TOP))
    cursor = VIEW_TOP - shift
    for m, h in zip(S.MSGS, slots):
        item_bottom = cursor + h
        cursor = item_bottom
        if h <= 0.5:
            continue
        if m["side"] == "ts":
            lay = text_arr(m["text"], INTER_M, 28, (142, 142, 147))
            blit(layer, lay, 540, item_bottom - 22, smooth((t - m["show"]) / 0.3))
            continue
        typing = m["side"] in ("ig", "fail") and t < m["show"]
        bb = item_bottom - (FAIL_LABEL_H if (m["side"] == "fail" and not typing) else 0)
        if typing:
            k = smooth((t - m["type_start"]) / 0.22)
            blit_bottom(layer, typing_bubble((t - m["type_start"]) / 1.1), CHAT_L, bb, k, 0.6 + 0.4 * ease_back(k, 1.3))
            continue
        side = m["side"]
        lay = bubble(m["text"], side)
        p = (t - m["show"]) / 0.30
        sc = 0.55 + 0.45 * ease_back(p, 2.0)
        a = smooth(p / 0.45)
        if side == "me":
            blit_bottom(layer, lay, CHAT_R, bb, a, sc, origin="r")
        else:
            blit_bottom(layer, lay, CHAT_L, bb, a, sc, origin="l")
        if side == "fail":
            la = smooth((t - m["show"] - 0.04) / 0.18)
            w, hb = lay[1].shape[1], lay[1].shape[0]
            disc = rr_layer(52, 52, 26, RED)
            blit_bottom(layer, disc, CHAT_L + w + 22, bb - (hb - 52) / 2, la, 1.0)
            blit(layer, text_arr("!", INTER_B, 40, (255, 255, 255)), CHAT_L + w + 22 + 26, bb - hb / 2 - 2, la)
            blit(layer, text_arr("Not delivered", INTER_SB, 36, (255, 92, 82)), CHAT_L + 8, item_bottom - 22, la, anchor="l")


_mask = None


def chat_mask():
    global _mask
    if _mask is None:
        y = np.arange(H, dtype=np.float32)
        top = np.clip((y - 335) / 100.0, 0, 1)
        bot = 1 - np.clip((y - (VIEW_BOTTOM + 8)) / 30.0, 0, 1)
        _mask = (top * top * (3 - 2 * top) * bot)[:, None, None].astype(np.float32)
    return _mask


# ----------------------------------------------------------------- header + status bar
_static = {}


def avatar_layer(d=92):
    SS = 3
    n = d * SS
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    t = (xx / n + (n - yy) / n) / 2
    c1, c2, c3 = np.array([95, 60, 210]), np.array([225, 40, 120]), np.array([255, 170, 60])
    col = np.where(t[..., None] < 0.55, c1 + (c2 - c1) * (t[..., None] / 0.55),
                   c2 + (c3 - c2) * ((t[..., None] - 0.55) / 0.45))
    img = Image.fromarray(col.astype(np.uint8)).convert("RGBA")
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, n - 1, n - 1), fill=255)
    img.putalpha(mask)
    d2 = ImageDraw.Draw(img)
    f = font(INTER_XB, 40 * SS)
    d2.text((n / 2, n / 2 + 1), "IG", font=f, fill=(255, 255, 255, 255), anchor="mm")
    img = img.resize((d, d), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    return arr[..., :3], arr[..., 3] / 255.0


def info_button():
    SS, d = 3, 64
    img = Image.new("RGBA", (d * SS, d * SS), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.ellipse((4 * SS, 4 * SS, (d - 4) * SS, (d - 4) * SS), outline=(10, 132, 255, 255), width=4 * SS)
    dr.text((d * SS / 2, d * SS / 2 + SS), "i", font=font(INTER_SB, 36 * SS), fill=(10, 132, 255, 255), anchor="mm")
    img = img.resize((d, d), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    return arr[..., :3], arr[..., 3] / 255.0


def chevron():
    SS, w, h = 3, 40, 70
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.line([(30 * SS, 8 * SS), (10 * SS, 35 * SS), (30 * SS, 62 * SS)], fill=(10, 132, 255, 255), width=7 * SS, joint="curve")
    img = img.resize((w, h), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    return arr[..., :3], arr[..., 3] / 255.0


def battery_layer(pct):
    SS, w, h = 3, 78, 40
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 2 * SS, 68 * SS, 38 * SS), radius=11 * SS, outline=(255, 255, 255, 150), width=3 * SS)
    d.rounded_rectangle((71 * SS, 14 * SS, 75 * SS, 26 * SS), radius=2 * SS, fill=(255, 255, 255, 150))
    d.rounded_rectangle((6 * SS, 8 * SS, (6 + 56 * pct / 100) * SS, 32 * SS), radius=6 * SS, fill=(255, 255, 255, 255))
    img = img.resize((w, h), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    return arr[..., :3], arr[..., 3] / 255.0


def signal_layer():
    SS, w, h = 3, 56, 40
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, hh in enumerate((12, 20, 28, 36)):
        x = i * 14
        d.rounded_rectangle((x * SS, (38 - hh) * SS, (x + 9) * SS, 38 * SS), radius=2 * SS, fill=(255, 255, 255, 255))
    img = img.resize((w, h), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    return arr[..., :3], arr[..., 3] / 255.0


def clock_text(t):
    s = S.CLOCK[0][1]
    for ts, c in S.CLOCK:
        if t >= ts:
            s = c
    return s


def draw_header(frame, t, ig_typing):
    if "av" not in _static:
        _static["av"] = avatar_layer()
        _static["info"] = info_button()
        _static["chev"] = chevron()
        _static["sig"] = signal_layer()
        _static["bat"] = battery_layer(41)
    blit(frame, text_arr(clock_text(t), INTER_SB, 42, (255, 255, 255)), 96, 108, 1.0, "l")
    blit(frame, _static["sig"], W - 270, 108, 1.0, "r")
    blit(frame, text_arr("5G", INTER_SB, 34, (255, 255, 255)), W - 258, 108, 1.0, "l")
    blit(frame, _static["bat"], W - 80, 108, 1.0, "r")
    blit(frame, _static["chev"], 82, 232, 1.0)
    blit(frame, _static["av"], 190, 232, 1.0)
    blit(frame, text_arr("Instagram", INTER_SB, 42, (255, 255, 255)), 258, 216, 1.0, "l")
    sub = "typing…" if ig_typing else "active now"
    blit(frame, text_arr(sub, INTER_M, 29, (60, 220, 120) if not ig_typing else (150, 150, 158)), 260, 258, 1.0, "l")
    blit(frame, _static["info"], 980, 232, 1.0)
    frame[318:320, :] = np.maximum(frame[318:320, :], 28)           # hairline under the header


# ----------------------------------------------------------------- keyboard + input
KB_Y0 = 1290
_kb = {}


def keyboard():
    if "img" in _kb:
        return _kb["img"], _kb["keys"]
    kh, gap = 104, 14
    panel_h = H - KB_Y0
    img = Image.new("RGB", (W, panel_h), (28, 28, 30))
    d = ImageDraw.Draw(img)
    keys = {}
    f = font(INTER_M, 46)
    rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    kw = 96
    y = 26
    for ri, row in enumerate(rows):
        total = len(row) * kw + (len(row) - 1) * 12
        x = (W - total) // 2
        if ri == 2:
            x = (W - (140 + 12 + total + 12 + 140)) // 2 + 152
            d.rounded_rectangle(((W - (140 + 12 + total + 12 + 140)) // 2, y, (W - (140 + 12 + total + 12 + 140)) // 2 + 140, y + kh),
                                radius=14, fill=(44, 44, 47))
            d.text(((W - (140 + 12 + total + 12 + 140)) // 2 + 70, y + kh / 2), "⇧", font=font("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44),
                   fill=(235, 235, 240), anchor="mm")
            xr = x + total + 12
            d.rounded_rectangle((xr, y, xr + 140, y + kh), radius=14, fill=(44, 44, 47))
            d.text((xr + 70, y + kh / 2), "⌫", font=font("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44),
                   fill=(235, 235, 240), anchor="mm")
        for ch in row:
            d.rounded_rectangle((x, y, x + kw, y + kh), radius=14, fill=(72, 72, 76))
            d.text((x + kw / 2, y + kh / 2), ch, font=f, fill=(255, 255, 255), anchor="mm")
            keys[ch] = (x, y, kw, kh)
            x += kw + 12
        y += kh + gap + 8
    # bottom row
    d.rounded_rectangle((16, y, 16 + 150, y + kh), radius=14, fill=(44, 44, 47))
    d.text((16 + 75, y + kh / 2), "123", font=font(INTER_M, 38), fill=(235, 235, 240), anchor="mm")
    d.rounded_rectangle((16 + 150 + 12, y, 16 + 150 + 12 + 560, y + kh), radius=14, fill=(72, 72, 76))
    keys[" "] = (16 + 150 + 12, y, 560, kh)
    d.rounded_rectangle((16 + 150 + 12 + 560 + 12, y, W - 16, y + kh), radius=14, fill=(44, 44, 47))
    d.text(((16 + 150 + 12 + 560 + 12 + W - 16) / 2, y + kh / 2), "return", font=font(INTER_M, 36), fill=(235, 235, 240), anchor="mm")
    arr = np.asarray(img, np.float32)
    _kb["img"], _kb["keys"] = arr, keys
    return arr, keys


_ktimes = {}


def my_typing_state(t):
    """(text typed so far, pressed char or None) for the input field"""
    for m in S.MSGS:
        if m["side"] != "me":
            continue
        if m["type_start"] <= t < m["show"]:
            kt = _ktimes.setdefault(m["text"], S.key_times(m))
            n = int(np.sum(kt <= t))
            pressed = None
            if n > 0 and t - kt[n - 1] < 0.09:
                pressed = m["text"][n - 1].lower()
            return m["text"][:n], pressed
    return "", None


def draw_keyboard(frame, t, pressed, slide):
    arr, keys = keyboard()
    y0 = KB_Y0 + int(slide)
    if y0 >= H:
        return
    h = min(arr.shape[0], H - y0)
    frame[y0:y0 + h] = arr[:h]
    if pressed and pressed in keys:
        x, y, kw, kh = keys[pressed]
        yy = y0 + y
        frame[yy:yy + kh, x:x + kw] = frame[yy:yy + kh, x:x + kw] * 0.55 + 255 * 0.45
        if pressed != " ":                      # the space bar has no pop-up on a real keyboard
            pop = rr_layer(int(kw * 1.45), int(kh * 1.5), 18, (110, 110, 116))
            blit_bottom(frame, pop, x - kw * 0.225, yy + 8, 1.0, 1.0, "l")
            blit(frame, text_arr(pressed, INTER_M, 62, (255, 255, 255)), x + kw / 2, yy - kh * 0.55, 1.0)


def draw_input(frame, t, typed, locked, lock_a):
    cy = 1190
    pill = rr_layer(835, 86, 43, (28, 28, 30), outline=(58, 58, 62), ow=2)
    blit(frame, pill, CHAT_L + 835 / 2, cy, 1.0)
    if locked:
        return
    if typed:
        blit(frame, text_arr(typed, INTER_M, 42, (255, 255, 255)), CHAT_L + 34, cy - 1, 1.0, "l")
        w = font(INTER_M, 42).getlength(typed)
        if int(t * 2.4) % 2 == 0:
            frame[cy - 28:cy + 28, int(CHAT_L + 36 + w):int(CHAT_L + 39 + w)] = np.array([10, 132, 255])
        sd = rr_layer(60, 60, 30, BLUE)
        blit(frame, sd, CHAT_L + 835 - 44, cy, 1.0)
        blit(frame, text_arr("↑", INTER_B, 40, (255, 255, 255)), CHAT_L + 835 - 44, cy - 1, 1.0)
    else:
        blit(frame, text_arr("Message", INTER_M, 42, (110, 110, 116)), CHAT_L + 34, cy - 1, 1.0, "l")


def lock_icon(size=150, color=(255, 255, 255)):
    SS = 3
    n = size * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bw, bh = n * 0.56, n * 0.42
    bx, by = (n - bw) / 2, n * 0.44
    d.arc((n * 0.28, n * 0.10, n * 0.72, n * 0.62), 180, 360, fill=color + (255,), width=int(n * 0.075))
    d.line((n * 0.285, n * 0.36, n * 0.285, n * 0.50), fill=color + (255,), width=int(n * 0.075))
    d.line((n * 0.715, n * 0.36, n * 0.715, n * 0.50), fill=color + (255,), width=int(n * 0.075))
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=n * 0.08, fill=color + (255,))
    d.ellipse((n / 2 - n * 0.045, by + bh * 0.28, n / 2 + n * 0.045, by + bh * 0.28 + n * 0.09), fill=(20, 20, 24, 255))
    d.rounded_rectangle((n / 2 - n * 0.018, by + bh * 0.48, n / 2 + n * 0.018, by + bh * 0.80), radius=n * 0.015, fill=(20, 20, 24, 255))
    img = img.resize((size, size), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    return arr[..., :3], arr[..., 3] / 255.0


# ----------------------------------------------------------------- overlays
_edge = None


def edge_mask():
    global _edge
    if _edge is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _edge = np.clip((d - 0.30) / 0.9, 0, 1) ** 1.5
    return _edge


def clock_face(frame, cx, cy, r, m_total, alpha):
    """analogue clock whose hands spin from 12:25 to 1:12 (next day)"""
    SS = 2
    n = int((r * 2 + 40) * SS)
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = n / 2
    d.ellipse((c - r * SS, c - r * SS, c + r * SS, c + r * SS), outline=(255, 255, 255, 255), width=8 * SS)
    for i in range(12):
        a = math.radians(i * 30)
        d.line((c + math.sin(a) * (r - 18) * SS, c - math.cos(a) * (r - 18) * SS,
                c + math.sin(a) * (r - 6) * SS, c - math.cos(a) * (r - 6) * SS), fill=(255, 255, 255, 200), width=4 * SS)
    ma = math.radians(150 + 6 * m_total)
    ha = math.radians(12.5 + 0.5 * m_total)
    d.line((c, c, c + math.sin(ma) * (r - 20) * SS, c - math.cos(ma) * (r - 20) * SS), fill=(255, 255, 255, 255), width=6 * SS)
    d.line((c, c, c + math.sin(ha) * (r * 0.55) * SS, c - math.cos(ha) * (r * 0.55) * SS), fill=(255, 255, 255, 255), width=9 * SS)
    d.ellipse((c - 8 * SS, c - 8 * SS, c + 8 * SS, c + 8 * SS), fill=(255, 255, 255, 255))
    img = img.resize((n // SS, n // SS), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    blit(frame, (arr[..., :3], arr[..., 3] / 255.0), cx, cy, alpha)


def touch(frame, x, y, press, alpha):
    r = int(44 * (1 - 0.18 * press))
    SS = 3
    n = (r * 2 + 12) * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = n / 2
    d.ellipse((c - r * SS, c - r * SS, c + r * SS, c + r * SS), fill=(255, 255, 255, 80), outline=(255, 255, 255, 200), width=4 * SS)
    img = img.resize((n // SS, n // SS), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    blit(frame, (arr[..., :3], arr[..., 3] / 255.0), x, y, alpha)


def ripple(frame, x, y, p, color=(255, 255, 255)):
    if not (0 < p < 1):
        return
    r = int(40 + 110 * ease_out(p))
    SS = 2
    n = (r * 2 + 12) * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = n / 2
    d.ellipse((c - r * SS, c - r * SS, c + r * SS, c + r * SS), outline=color + (255,), width=5 * SS)
    img = img.resize((n // SS, n // SS), Image.LANCZOS)
    arr = np.asarray(img, np.float32)
    blit(frame, (arr[..., :3], arr[..., 3] / 255.0), x, y, 0.8 * (1 - p))


ALERT = dict(cx=540, cy=760, w=780, h=390)
INFO_XY = (980, 232)
CANCEL_XY = (540 - 195, 760 + 195 - 55)
BLOCK_XY = (540 + 195, 760 + 195 - 55)


def alert_layer(block_pressed):
    key = ("alert", block_pressed)
    if key in _static:
        return _static[key]
    a = ALERT
    base = rr_layer(a["w"], a["h"], 46, (46, 46, 50))
    rgb = base[0].copy()
    al = base[1].copy()
    img = Image.fromarray(rgb.astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.text((a["w"] / 2, 80), "Block Instagram?", font=font(INTER_SB, 56), fill=(255, 255, 255), anchor="mm")
    d.text((a["w"] / 2, 156), "It won't be able to message", font=font(INTER_M, 37), fill=(214, 214, 220), anchor="mm")
    d.text((a["w"] / 2, 204), "you again until 8:00.", font=font(INTER_M, 37), fill=(214, 214, 220), anchor="mm")
    by = a["h"] - 110
    d.line((0, by, a["w"], by), fill=(84, 84, 90), width=2)
    d.line((a["w"] / 2, by, a["w"] / 2, a["h"]), fill=(84, 84, 90), width=2)
    if block_pressed:
        d.rectangle((a["w"] / 2 + 1, by + 2, a["w"] - 1, a["h"] - 24), fill=(70, 70, 76))
    d.text((a["w"] / 4, by + 55), "Cancel", font=font(INTER_M, 44), fill=BLUE, anchor="mm")
    d.text((a["w"] * 3 / 4, by + 55), "Block", font=font(INTER_B, 44), fill=RED, anchor="mm")
    out = (np.asarray(img, np.float32), al)
    _static[key] = out
    return out


def finger_pos(t):
    """touch-indicator position + press amount + alpha"""
    pts = [(S.FINGER_IN, (905, 1480)), (S.INFO_TAP - 0.05, INFO_XY), (S.INFO_TAP + 0.30, INFO_XY),
           (S.INFO_TAP + 0.75, (610, 935)), (S.BLOCK_TAP - 0.36, (610, 935)), (S.BLOCK_TAP - 0.06, BLOCK_XY)]
    x, y = pts[0][1]
    for (t0, p0), (t1, p1) in zip(pts[:-1], pts[1:]):
        if t >= t0:
            u = ease_io((t - t0) / max(1e-6, t1 - t0)) if t < t1 else 1.0
            x, y = p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u
    if S.INFO_TAP + 0.75 < t < S.BLOCK_TAP - 0.36:            # nervous tremble while hovering
        x += math.sin(t * 61) * 3.5
        y += math.cos(t * 53) * 3.5
    press = max(smooth(1 - abs(t - S.INFO_TAP) / 0.09), smooth(1 - abs(t - S.BLOCK_TAP) / 0.09))
    a = smooth((t - S.FINGER_IN) / 0.25) * (1 - smooth((t - (S.BLOCK_TAP + 0.12)) / 0.2))
    return x, y, press, a


# ----------------------------------------------------------------- CTA card
def draw_cta(t):
    frame = np.zeros((H, W, 3), np.float32)
    p = t - S.CTA_IN
    # background glow
    yy = np.arange(H, dtype=np.float32)[:, None]
    xx = np.arange(W, dtype=np.float32)[None, :]
    g = np.exp(-(((yy - 830) / 520) ** 2 + ((xx - 540) / 520) ** 2)) * 0.55 * smooth(p / 0.6)
    frame[..., 0] += g * 70
    frame[..., 1] += g * 8
    frame[..., 2] += g * 14

    def pop(delay, dur=0.32):
        q = (p - delay) / dur
        return smooth(q / 0.5), 0.8 + 0.2 * ease_back(q, 2.2)

    a, s = pop(0.05)
    blit(frame, text_arr("Comment", SERIF, 168, (255, 255, 255)), 540, 590, a, scale=s)
    a, s = pop(0.30)
    pulse = 1.0 + 0.025 * math.sin(max(0.0, p - 0.7) * 2 * math.pi * 1.6)
    pill = rr_layer(640, 190, 54, RED)
    blit(frame, pill, 540, 800, a, scale=s * pulse)
    blit(frame, text_arr("BLOCK", INTER_XB, 128, (255, 255, 255), tracking=4), 540, 802, a, scale=s * pulse)
    a, s = pop(0.62, 0.4)
    blit(frame, text_arr("Get your first 30 days free", INTER_SB, 50, (240, 240, 246)), 540, 1010, a, scale=1.0)
    a, s = pop(0.80, 0.4)
    blit(frame, text_arr("when it opens.", INTER_M, 50, (180, 180, 190)), 540, 1078, a, scale=1.0)
    return frame


# ----------------------------------------------------------------- one frame
def haptic(t):
    dx = dy = 0.0
    for m in S.MSGS:
        if m["side"] in ("ig", "fail"):
            dt = t - m["show"]
            if 0 <= dt < 0.34:
                a = 7.0 * math.exp(-dt / 0.09)
                dx += a * math.sin(dt * 95)
                dy += a * 0.6 * math.cos(dt * 83)
    return dx, dy


def render(f):
    t = f / FPS
    if t >= S.CTA_IN:
        frame = draw_cta(t)
        fo = smooth((S.DURATION - t) / 0.25)
        return np.clip(frame * fo, 0, 255).astype(np.uint8)

    frame = np.zeros((H, W, 3), np.float32)
    layer = np.zeros((H, W, 3), np.float32)
    draw_chat(layer, t)
    frame += layer * chat_mask()

    ig_typing = any(m["side"] in ("ig", "fail") and m["type_start"] <= t < m["show"] for m in S.MSGS)
    draw_header(frame, t, ig_typing)

    # keyboard / input
    blocked = t >= S.BLOCK_TAP
    k0, k1 = S.KEYBOARD_DOWN
    slide = (H - KB_Y0) * ease_io((t - k0) / (k1 - k0)) if blocked else 0.0
    typed, pressed = my_typing_state(t)
    draw_keyboard(frame, t, pressed, slide)
    draw_input(frame, t, typed, locked=t >= S.LOCK_OUT - 0.15, lock_a=1.0)
    if t >= S.LOCK_OUT - 0.15:
        a = smooth((t - (S.LOCK_OUT - 0.15)) / 0.3)
        blit(frame, lock_icon(46, (150, 150, 158)), CHAT_L + 70, 1190, a)
        blit(frame, text_arr("Instagram is blocked until 8:00", INTER_M, 36, (150, 150, 158)), CHAT_L + 118, 1190, a, "l")

    # ---- time skip: dim, spinning clock, "47 min later"
    if S.SKIP_IN <= t < S.SKIP_OUT + 0.4:
        ain = smooth((t - S.SKIP_IN) / 0.5)
        aout = 1 - smooth((t - S.SKIP_OUT) / 0.35)
        a = 0.93 * ain * aout
        frame *= 1 - a
        pr = clamp01((t - (S.SKIP_IN + 0.15)) / (S.SKIP_SLAM - S.SKIP_IN - 0.15))
        m_total = 767 * ease_io(pr)
        clock_face(frame, 540, 600, 110, m_total, ain * aout)
        if t >= S.SKIP_SLAM:
            q = (t - S.SKIP_SLAM) / 0.30
            sc = 1.0 + 0.5 * (1 - ease_out(q))
            lay = text_arr("47 min later", SERIF, 150, (255, 255, 255))
            blit(frame, lay, 540, 850, smooth(q * 4) * aout, scale=sc)
            fl = 0.7 * max(0.0, 1 - (t - S.SKIP_SLAM) / 0.18) ** 1.5
            if fl > 0:
                frame += (255 - frame) * fl

    # ---- tension: red vignette + heartbeat
    if t >= S.TENSION_IN and t < S.LOCK_IN:
        ramp = smooth((t - S.TENSION_IN) / 5.0)
        bpm = 62 + 28 * ramp
        beat = max(0.0, math.sin(2 * math.pi * (t - S.TENSION_IN) * bpm / 60 * 1.0)) ** 6
        v = (0.18 + 0.38 * ramp) * (0.65 + 0.35 * beat)
        em = edge_mask()
        frame[..., 0] += 150 * v * em
        frame[..., 1] -= 30 * v * em
        frame[..., 2] -= 30 * v * em

    # ---- block: dim, alert, finger
    if S.ALERT_IN <= t < S.BLOCK_TAP + 0.18:
        ain = smooth((t - S.ALERT_IN) / 0.18)
        aout = 1 - smooth((t - S.BLOCK_TAP - 0.02) / 0.14)
        frame *= 1 - 0.55 * ain * aout
        lay = alert_layer(abs(t - S.BLOCK_TAP) < 0.07 or t > S.BLOCK_TAP)
        sc = 1.06 - 0.06 * ease_out((t - S.ALERT_IN) / 0.2)
        blit(frame, (lay[0], lay[1]), ALERT["cx"], ALERT["cy"], ain * aout, scale=sc)
    if S.FINGER_IN <= t < S.BLOCK_TAP + 0.4:
        x, y, press, a = finger_pos(t)
        ripple(frame, INFO_XY[0], INFO_XY[1], (t - S.INFO_TAP) / 0.45)
        ripple(frame, BLOCK_XY[0], BLOCK_XY[1], (t - S.BLOCK_TAP) / 0.5, (255, 69, 58))
        if a > 0.01:
            touch(frame, x, y, press, a)

    # ---- lock card
    if S.LOCK_IN <= t < S.LOCK_OUT + 0.1:
        ain = smooth((t - S.LOCK_IN) / 0.16)
        aout = 1 - smooth((t - (S.LOCK_OUT - 0.2)) / 0.3)
        frame *= 1 - 0.95 * ain * aout
        q = (t - S.LOCK_IN) / 0.35
        sc = 0.7 + 0.3 * ease_back(q, 2.4)
        pulse = 1 + 0.03 * math.sin((t - S.LOCK_IN) * 9)
        blit(frame, lock_icon(300, (255, 255, 255)), 540, 610, ain * aout, scale=sc * pulse)
        blit(frame, text_arr("Instagram is blocked", INTER_B, 72, (255, 255, 255)), 540, 835, smooth(q * 1.2) * ain * aout, scale=sc)
        blit(frame, text_arr("until 8:00.", INTER_B, 72, (255, 110, 100)), 540, 925, smooth((q - 0.15) * 1.2) * ain * aout, scale=sc)

    # ---- impact flash + glitch on Block
    dt = t - S.BLOCK_TAP
    if 0 <= dt < 0.22:
        fl = 0.55 * (1 - dt / 0.22) ** 1.6
        frame += (255 - frame) * fl
        sh = int(16 * (1 - dt / 0.22))
        if sh:
            frame[..., 0] = np.roll(frame[..., 0], sh, axis=1)
            frame[..., 2] = np.roll(frame[..., 2], -sh, axis=1)

    # ---- haptic shake on every incoming message
    dx, dy = haptic(t)
    if abs(dx) > 0.5 or abs(dy) > 0.5:
        frame = np.roll(np.roll(frame, int(round(dx)), axis=1), int(round(dy)), axis=0)

    # open / close
    frame *= smooth(t / 0.15)
    return np.clip(frame, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------- main
def mux(video, wav, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", "loudnorm=I=-14:TP=-2:LRA=9,alimiter=limit=0.89:level=disabled", "-c:a", "aac", "-b:a", "192k", "-t", f"{S.DURATION}",
                    "-movflags", "+faststart", out], check=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[1] == "--stills":
        d = os.path.join(OUT, "stills_b")
        os.makedirs(d, exist_ok=True)
        for tt in sys.argv[2].split(","):
            Image.fromarray(render(int(round(float(tt) * FPS)))).save(os.path.join(d, f"b_{float(tt):05.2f}.png"))
            print("saved", tt)
        return
    import sound
    video = os.path.join(OUT, "_breakup_video.mp4")
    if "--audio-only" not in sys.argv:
        enc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
             "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264",
             "-preset", "medium", "-crf", "19", "-maxrate", "14M", "-bufsize", "28M", "-colorspace", "bt709",
             "-color_primaries", "bt709", "-color_trc", "bt709", "-an", video], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for fr in pool.imap(render, range(S.TOTAL_FRAMES), chunksize=4):
                enc.stdin.write(fr.tobytes())
        enc.stdin.close()
        enc.wait()
        print("video rendered", flush=True)
    wav = os.path.join(OUT, "_breakup_mix.wav")
    sound.build_mix(wav, with_music=True)
    mux(video, wav, os.path.join(OUT, "breakup.mp4"))
    wav2 = os.path.join(OUT, "_breakup_mix_nomusic.wav")
    sound.build_mix(wav2, with_music=False)
    mux(video, wav2, os.path.join(OUT, "breakup_no_music.mp4"))
    print("done")


if __name__ == "__main__":
    main()
