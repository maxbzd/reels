"""Compositing toolkit for the 'film' version: put our own UI onto the phone screen in real footage,
fly the camera into it, and grade everything.

Coordinates: footage = 1280x720 px;  output = 1080x1920 (9:16);  UI canvas = 1080 x 2200 px
(the 1080x1920 'reel frame' sits in rows 140..2060, so the screen is as tall as the real phone's).
"""
import subprocess

import cv2
import numpy as np

W, H = 1080, 1920
CH = 2200
PAD = (CH - H) // 2                       # 140
CANVAS_CORNERS = np.array([[0, 0], [W, 0], [W, CH], [0, CH]], np.float32)
FULL_CORNERS = np.array([[0, -PAD], [W, -PAD], [W, H + PAD], [0, H + PAD]], np.float32)   # canvas at p = 1


def ease_io(x):
    x = min(1.0, max(0.0, x))
    return 0.5 * (1 - np.cos(np.pi * x))


def ease_out5(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 4


# ----------------------------------------------------------------- footage
class Footage:
    """a decoded segment of a clip (RGB, 1280x720) addressed by clip time"""

    def __init__(self, path, t0, t1):
        info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                               "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
        a, b = info.split("/")
        self.fps = float(a) / float(b)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0}", "-t", f"{t1 - t0}", "-i", path, "-vf", "scale=1280:720",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        self.frames = np.frombuffer(raw, np.uint8).reshape(-1, 720, 1280, 3)
        self.t0 = t0

    def at(self, t):
        """frame at clip time t (blends neighbours so slow-motion stays smooth)"""
        x = (t - self.t0) * self.fps
        x = min(max(x, 0), len(self.frames) - 1.001)
        i = int(x)
        f = x - i
        if f < 0.02:
            return self.frames[i]
        return cv2.addWeighted(self.frames[i], 1 - f, self.frames[i + 1], f, 0)


def interp_quad(keys, t):
    """keys: [(t, 4x2 array)] -> smooth quad at time t (Catmull-style via cosine ease between keys)"""
    if t <= keys[0][0]:
        return np.array(keys[0][1], np.float32)
    for (ta, qa), (tb, qb) in zip(keys[:-1], keys[1:]):
        if ta <= t <= tb:
            u = ease_io((t - ta) / (tb - ta))
            return (1 - u) * np.array(qa, np.float32) + u * np.array(qb, np.float32)
    return np.array(keys[-1][1], np.float32)


# ----------------------------------------------------------------- camera
def frame_map(cx, cy, zoom, roll=0.0):
    """footage -> output similarity: footage point (cx,cy) lands in the middle; zoom=1 shows 405x720 px of footage"""
    sc = (H / 720.0) * zoom
    c, s = np.cos(np.radians(roll)), np.sin(np.radians(roll))
    A = np.array([[sc * c, -sc * s, 0], [sc * s, sc * c, 0], [0, 0, 1]], np.float64)
    T1 = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]], np.float64)
    T2 = np.array([[1, 0, W / 2], [0, 1, H / 2], [0, 0, 1]], np.float64)
    return T2 @ A @ T1


def apply_h(M, pts):
    p = np.hstack([np.array(pts, np.float64), np.ones((len(pts), 1))]) @ M.T
    return (p[:, :2] / p[:, 2:3]).astype(np.float32)


# ----------------------------------------------------------------- skin / occlusion
TOL = 26.0


def skin_over_screen(frame_rgb, qf):
    """mask (footage coords, 0..1) of fingers lying over the screen quad.
    Seeds = skin pixels of the hand just outside the screen; the mask grows into the screen only through
    pixels whose colour is close to THIS hand's colour (so pizzas / sushi on the old screen are not picked up)."""
    x0, y0 = np.maximum(qf.min(0).astype(int) - 60, 0)
    x1, y1 = np.minimum(qf.max(0).astype(int) + 60, [1280, 720])
    roi = cv2.GaussianBlur(frame_rgb[y0:y1, x0:x1], (0, 0), 1.6)
    ycc = cv2.cvtColor(roi, cv2.COLOR_RGB2YCrCb).astype(np.int32)
    cr, cb, yy = ycc[..., 1], ycc[..., 2], ycc[..., 0]
    loose = ((cr > 136) & (cr < 178) & (cb > 80) & (cb < 130) & (yy > 60)).astype(np.uint8)
    qloc = (qf - [x0, y0]).astype(np.int32)
    inside = np.zeros(loose.shape, np.uint8)
    cv2.fillConvexPoly(inside, qloc, 1)
    ring = cv2.dilate(inside, np.ones((25, 25), np.uint8)) & (1 - inside)
    seeds = loose & ring
    if seeds.sum() < 150:
        return np.zeros((720, 1280), np.float32)
    lab = cv2.cvtColor(roi, cv2.COLOR_RGB2LAB).astype(np.float32)
    ref = np.median(lab[seeds > 0], axis=0)
    d = np.sqrt(((lab[..., 0] - ref[0]) * 0.6) ** 2 + (lab[..., 1] - ref[1]) ** 2 + (lab[..., 2] - ref[2]) ** 2)
    mx = roi.max(2).astype(np.float32)
    mn = roi.min(2).astype(np.float32)
    sat = (mx - mn) / np.maximum(mx, 1) * 255.0
    distin = cv2.distanceTransform(inside, cv2.DIST_L2, 3)              # px from the screen edge, inside it
    allowed = ((d < TOL) & (loose > 0) & (sat < 128) & ((distin < 62) | (inside == 0))).astype(np.uint8)
    marker = (seeds & allowed).astype(np.uint8)
    k = np.ones((3, 3), np.uint8)
    for _ in range(70):
        grown = cv2.dilate(marker, k) & allowed
        if grown.sum() == marker.sum():
            break
        marker = grown
    marker = cv2.morphologyEx(marker, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)) & cv2.dilate(allowed, np.ones((9, 9), np.uint8))
    marker = cv2.erode(marker, np.ones((3, 3), np.uint8), iterations=2)
    keep = (marker & inside) * 255
    keep = cv2.GaussianBlur(keep.astype(np.uint8), (5, 5), 0)
    out = np.zeros((720, 1280), np.float32)
    out[y0:y1, x0:x1] = keep / 255.0
    return out


def grow_quad(q, k=1.045, shift=(0.0, 0.0)):
    """enlarge the screen quad a little so the UI fully covers the lit screen (hides the old screen's edge)"""
    c = q.mean(0)
    return ((q - c) * k + c + np.array(shift, np.float32)).astype(np.float32)


# ----------------------------------------------------------------- compositing
_corner_mask = None


def canvas_alpha():
    global _corner_mask
    if _corner_mask is None:
        m = np.zeros((CH, W), np.uint8)
        cv2.rectangle(m, (0, 0), (W - 1, CH - 1), 255, -1, cv2.LINE_AA)
        r = 70
        # rounded corners
        mask = np.zeros((CH, W), np.uint8)
        cv2.rectangle(mask, (r, 0), (W - r, CH), 255, -1)
        cv2.rectangle(mask, (0, r), (W, CH - r), 255, -1)
        for cx, cy in ((r, r), (W - r, r), (r, CH - r), (W - r, CH - r)):
            cv2.circle(mask, (cx, cy), r, 255, -1, cv2.LINE_AA)
        _corner_mask = mask.astype(np.float32) / 255.0
    return _corner_mask


def render_shot(frame_rgb, qf, ui_canvas, S, e, bg_grade=None, glow=0.30, occlude=True, samples=1, e_next=None):
    """one output frame: footage framed by S, UI on the screen quad, camera 'flying' into the screen as e: 0 -> 1.
    samples>1 averages a few sub-steps between e and e_next for motion blur."""
    skin = skin_over_screen(frame_rgb, qf) if (occlude and e < 0.75) else None
    acc = np.zeros((H, W, 3), np.float32)
    for k in range(samples):
        ek = e if samples == 1 else e + (e_next - e) * (k / (samples - 1))
        q0 = apply_h(S, qf)
        C = (1 - ek) * q0 + ek * FULL_CORNERS
        Hbg = cv2.getPerspectiveTransform(qf.astype(np.float32), C.astype(np.float32))
        bg = cv2.warpPerspective(frame_rgb, Hbg, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        if bg_grade is not None:
            bg = bg_grade(bg)
        Hui = cv2.getPerspectiveTransform(CANVAS_CORNERS, C.astype(np.float32))
        ui = cv2.warpPerspective(ui_canvas, Hui, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT).astype(np.float32)
        al = cv2.warpPerspective(canvas_alpha(), Hui, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        if skin is not None:
            occ = cv2.warpPerspective(skin, Hbg, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            al = al * (1 - np.clip(occ * 1.15, 0, 1))
        # screen light spilling on the hand / face (only while the phone is small in frame)
        if glow > 0 and ek < 0.9:
            halo = cv2.GaussianBlur(ui * al[..., None], (0, 0), 70)
            bg = bg + halo * glow * (1 - ek)
        acc += bg * (1 - al[..., None]) + ui * al[..., None]
    return np.clip(acc / samples, 0, 255)


# ----------------------------------------------------------------- look
_vig = None


def grade(img, warm=1.0, night=0.0, lift=0.0):
    """filmic look: lifted blacks, teal in the shadows, warm highlights, soft contrast curve; 'night' dims it"""
    x = img / 255.0
    lum = x.mean(2, keepdims=True)
    x = x * (1 - night * 0.45)
    # teal shadows / orange highlights
    shadow = np.clip(1 - lum * 2.2, 0, 1)
    high = np.clip(lum * 2.0 - 0.7, 0, 1)
    x = x + shadow * np.array([-0.012, 0.010, 0.030]) * (1 + night) + high * np.array([0.030, 0.008, -0.020]) * warm
    # S curve
    x = np.clip(x, 0, 1)
    x = x * x * (3 - 2 * x) * 0.55 + x * 0.45
    x = x * (1 - lift) + lift * 0.04
    return np.clip(x * 255.0, 0, 255)


def vignette(img, strength=0.55):
    global _vig
    if _vig is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
        _vig = np.clip(d, 0, 1.4)
    return img * (1 - strength * np.clip(_vig - 0.35, 0, 1)[..., None] ** 1.6)


_rng = np.random.default_rng(5)


def grain(img, amount=3.2):
    n = _rng.standard_normal((H, W, 1), dtype=np.float32) * amount
    lum = img.mean(2, keepdims=True) / 255.0
    return img + n * (0.5 + 0.9 * (1 - lum))


def sharpen(img, amount=0.55):
    blur = cv2.GaussianBlur(img, (0, 0), 2.2)
    return img + (img - blur) * amount
