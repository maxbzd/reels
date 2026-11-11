"""The Reels-style feed that the hero scrolls on his phone: a static UI overlay (PNG, 1080x2200 canvas) over
a swiping stack of vertical clips (built once with ffmpeg xfade), plus the notification banner."""
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import comp

W, H, CH, PAD = comp.W, comp.H, comp.CH, comp.PAD
HERE = os.path.dirname(os.path.abspath(__file__))
INTER_M = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
INTER_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
INTER_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
INTER_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
SS = 3


def _f(p, s):
    return ImageFont.truetype(p, int(s * SS))


def heart(d, cx, cy, r, w=7, fill=None, col=(255, 255, 255, 255)):
    pts = []
    for i in range(0, 360, 4):
        t = math.radians(i)
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append(((cx + x * r / 17) * SS, (cy + y * r / 17) * SS))
    if fill:
        d.polygon(pts, fill=fill)
    d.line(pts + [pts[0]], fill=col, width=int(w * SS), joint="curve")


def comment(d, cx, cy, r, w=7):
    box = ((cx - r) * SS, (cy - r * 0.9) * SS, (cx + r) * SS, (cy + r * 0.75) * SS)
    d.rounded_rectangle(box, radius=r * 0.9 * SS, outline=(255, 255, 255, 255), width=int(w * SS))
    d.polygon([((cx - r * 0.55) * SS, (cy + r * 0.68) * SS), ((cx - r * 0.95) * SS, (cy + r * 1.1) * SS), ((cx - r * 0.1) * SS, (cy + r * 0.72) * SS)],
              fill=(0, 0, 0, 0))
    d.line([((cx - r * 0.7) * SS, (cy + r * 0.62) * SS), ((cx - r * 0.95) * SS, (cy + r * 1.05) * SS), ((cx - r * 0.2) * SS, (cy + r * 0.72) * SS)],
           fill=(255, 255, 255, 255), width=int(w * SS), joint="curve")


def plane(d, cx, cy, r, w=7):
    p = [((cx + r) * SS, (cy - r * 0.9) * SS), ((cx - r) * SS, (cy - r * 0.15) * SS), ((cx - r * 0.1) * SS, (cy + r * 0.2) * SS),
         ((cx + r) * SS, (cy - r * 0.9) * SS), ((cx + r * 0.2) * SS, (cy + r * 0.95) * SS), ((cx - r * 0.1) * SS, (cy + r * 0.2) * SS)]
    d.line(p, fill=(255, 255, 255, 255), width=int(w * SS), joint="curve")


def dots(d, cx, cy, r):
    for k in (-1, 0, 1):
        d.ellipse(((cx - r * 0.2) * SS, (cy + k * r * 0.7 - r * 0.2) * SS, (cx + r * 0.2) * SS, (cy + k * r * 0.7 + r * 0.2) * SS), fill=(255, 255, 255, 255))


def tabbar(d, y):
    cols = [108, 324, 540, 756, 972]
    wcol = (255, 255, 255, 255)
    # home
    cx = cols[0]
    d.line([((cx - 30) * SS, (y + 6) * SS), (cx * SS, (y - 24) * SS), ((cx + 30) * SS, (y + 6) * SS)], fill=wcol, width=6 * SS, joint="curve")
    d.rounded_rectangle(((cx - 22) * SS, (y - 8) * SS, (cx + 22) * SS, (y + 30) * SS), radius=4 * SS, outline=wcol, width=6 * SS)
    # search
    cx = cols[1]
    d.ellipse(((cx - 24) * SS, (y - 26) * SS, (cx + 16) * SS, (y + 14) * SS), outline=wcol, width=6 * SS)
    d.line([((cx + 12) * SS, (y + 10) * SS), ((cx + 30) * SS, (y + 28) * SS)], fill=wcol, width=6 * SS)
    # reels (active)
    cx = cols[2]
    d.rounded_rectangle(((cx - 30) * SS, (y - 30) * SS, (cx + 30) * SS, (y + 30) * SS), radius=10 * SS, fill=wcol)
    d.polygon([((cx - 8) * SS, (y - 14) * SS), ((cx - 8) * SS, (y + 14) * SS), ((cx + 16) * SS, y * SS)], fill=(0, 0, 0, 255))
    # shop
    cx = cols[3]
    d.rounded_rectangle(((cx - 26) * SS, (y - 14) * SS, (cx + 26) * SS, (y + 30) * SS), radius=6 * SS, outline=wcol, width=6 * SS)
    d.arc(((cx - 14) * SS, (y - 30) * SS, (cx + 14) * SS, (y + 4) * SS), 180, 360, fill=wcol, width=6 * SS)
    # profile
    cx = cols[4]
    d.ellipse(((cx - 28) * SS, (y - 28) * SS, (cx + 28) * SS, (y + 28) * SS), outline=wcol, width=6 * SS)
    d.ellipse(((cx - 10) * SS, (y - 16) * SS, (cx + 10) * SS, (y + 4) * SS), fill=wcol)
    d.pieslice(((cx - 20) * SS, (y + 2) * SS, (cx + 20) * SS, (y + 36) * SS), 180, 360, fill=wcol)


def build_overlay(path):
    img = Image.new("RGBA", (W * SS, CH * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    o = PAD   # 1080x1920 reel frame starts at canvas row 140
    # soft gradients top / bottom for legibility
    g = np.zeros((CH, W, 4), np.uint8)
    yy = np.arange(CH)[:, None]
    top = np.clip(1 - (yy - o) / 360.0, 0, 1) ** 1.6 * 150
    bot = np.clip((yy - (o + 1180)) / 760.0, 0, 1) ** 1.4 * 190
    g[..., 3] = np.maximum(top, bot).astype(np.uint8).repeat(W, 1)
    base = Image.fromarray(g, "RGBA").resize((W * SS, CH * SS), Image.BILINEAR)
    img.alpha_composite(base)
    d = ImageDraw.Draw(img)
    # header: "Reels" + camera
    d.text((60 * SS, (o + 172) * SS), "Reels", font=_f(INTER_B, 64), fill=(255, 255, 255, 255), anchor="lm")
    d.rounded_rectangle(((960 - 34) * SS, (o + 172 - 24) * SS, (960 + 34) * SS, (o + 172 + 30) * SS), radius=10 * SS, outline=(255, 255, 255, 255), width=6 * SS)
    d.ellipse(((960 - 14) * SS, (o + 172 - 6) * SS, (960 + 14) * SS, (o + 172 + 22) * SS), outline=(255, 255, 255, 255), width=6 * SS)
    # right column
    x = 985
    heart(d, x, o + 1010, 34)
    d.text((x * SS, (o + 1078) * SS), "12.4K", font=_f(INTER_SB, 30), fill=(255, 255, 255, 255), anchor="mm")
    comment(d, x, o + 1170, 32)
    d.text((x * SS, (o + 1238) * SS), "238", font=_f(INTER_SB, 30), fill=(255, 255, 255, 255), anchor="mm")
    plane(d, x, o + 1330, 32)
    d.text((x * SS, (o + 1398) * SS), "1,904", font=_f(INTER_SB, 30), fill=(255, 255, 255, 255), anchor="mm")
    dots(d, x, o + 1475, 30)
    d.rounded_rectangle(((x - 28) * SS, (o + 1540) * SS, (x + 28) * SS, (o + 1596) * SS), radius=10 * SS, outline=(255, 255, 255, 255), width=5 * SS)
    # bottom-left: avatar + name + caption
    d.ellipse((50 * SS, (o + 1440) * SS, 126 * SS, (o + 1516) * SS), fill=(140, 110, 255, 255), outline=(255, 255, 255, 255), width=4 * SS)
    d.text((88 * SS, (o + 1478) * SS), "w", font=_f(INTER_B, 38), fill=(255, 255, 255, 255), anchor="mm")
    d.text((146 * SS, (o + 1478) * SS), "wander.lust", font=_f(INTER_SB, 38), fill=(255, 255, 255, 255), anchor="lm")
    d.rounded_rectangle((420 * SS, (o + 1452) * SS, 556 * SS, (o + 1504) * SS), radius=12 * SS, outline=(255, 255, 255, 255), width=3 * SS)
    d.text((488 * SS, (o + 1478) * SS), "Follow", font=_f(INTER_SB, 30), fill=(255, 255, 255, 255), anchor="mm")
    d.text((50 * SS, (o + 1556) * SS), "golden hour never gets old", font=_f(INTER_M, 38), fill=(255, 255, 255, 255), anchor="lm")
    d.text((50 * SS, (o + 1610) * SS), "Original audio · wander.lust", font=_f(INTER_M, 30), fill=(235, 235, 240, 255), anchor="lm")
    # tab bar
    d.rectangle((0, (o + 1740) * SS, W * SS, CH * SS), fill=(0, 0, 0, 235))
    tabbar(d, o + 1822)
    # status bar (same as the chat's)
    img = img.resize((W, CH), Image.LANCZOS)
    img.save(path)


def build_feed_video(path, clips, seg=1.45, swipe=0.30, total=11.0):
    """vertical clips stacked with 'slideup' swipes -> 1080x2200 mp4"""
    n = len(clips)
    inputs, filt = [], []
    for i, (cid, ss) in enumerate(clips):
        inputs += ["-ss", str(ss), "-t", str(seg + swipe + 0.2), "-i", os.path.join(HERE, "assets", "clips", f"{cid}.mp4")]
        filt.append(f"[{i}:v]scale=-2:{CH}:flags=lanczos,crop={W}:{CH},fps=30,setsar=1,format=yuv420p,eq=contrast=1.06:saturation=1.1[v{i}]")
    cur = "v0"
    for i in range(1, n):
        off = i * seg - swipe * 0 - 0.0
        filt.append(f"[{cur}][v{i}]xfade=transition=slideup:duration={swipe}:offset={i * seg - swipe + 0.0:.3f}[x{i}]")
        cur = f"x{i}"
    cmd = ["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(filt), "-map", f"[{cur}]", "-t", f"{total}",
                                                       "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", path]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "assets", "ui"), exist_ok=True)
    build_overlay(os.path.join(HERE, "assets", "ui", "reels_overlay.png"))
    build_feed_video(os.path.join(HERE, "assets", "ui", "feed.mp4"),
                     [(32, 3.0), (16, 6.5), (149, 0.4), (74, 3.5), (126, 1.5), (63, 6.0), (150, 3.0), (32, 8.0)])
    print("ok")
