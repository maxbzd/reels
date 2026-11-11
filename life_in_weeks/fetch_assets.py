"""Download the free-licence footage, music and font used by the reel.

Sources (all free for commercial use, no attribution required):
  * Video + music: Mixkit  - https://mixkit.co/license/
  * Font: Instrument Serif - SIL Open Font License 1.1

Usage: python3 fetch_assets.py
"""
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

CLIPS = {
    # id: (url, what it is)
    32: ("https://assets.mixkit.co/videos/2385/2385-1080.mp4", "Man enjoying the wind"),
    31: ("https://assets.mixkit.co/videos/51791/51791-1080.mp4", "Forest and mountains, aerial (vertical)"),
    149: ("https://assets.mixkit.co/videos/23582/23582-720.mp4", "Friends running in the countryside"),
    16: ("https://assets.mixkit.co/videos/50267/50267-1080.mp4", "Landscape with a road at sunset"),
    63: ("https://assets.mixkit.co/videos/50561/50561-1080.mp4", "Explorer walks to the waterfall"),
    126: ("https://assets.mixkit.co/videos/1114/1114-1080.mp4", "Woman walking into the ocean"),
    74: ("https://assets.mixkit.co/videos/4840/4840-1080.mp4", "Woman during a sunset on a rooftop"),
    150: ("https://assets.mixkit.co/videos/37008/37008-720.mp4", "Friends enjoying sunset on the seashore"),
    165: ("https://assets.mixkit.co/videos/36985/36985-720.mp4", "Cheerful man raising arms surrounded by mountains"),
    53: ("https://assets.mixkit.co/videos/1214/1214-1080.mp4", "Woman's silhouette walking on the beach at sunset (vertical)"),
    164: ("https://assets.mixkit.co/videos/36979/36979-720.mp4", "Mountaineer walking on a cliff in a winter mountain range"),
    143: ("https://assets.mixkit.co/videos/39767/39767-1080.mp4", "Family walking together in nature (vertical)"),
}
MUSIC = {}   # music is supplied by the author: assets/music/luminary.mp3 (Joel Sunny - Luminary)
FONTS = {
    "InstrumentSerif-Regular.ttf":
        "https://raw.githubusercontent.com/google/fonts/main/ofl/instrumentserif/InstrumentSerif-Regular.ttf",
    "InstrumentSerif-Italic.ttf":
        "https://raw.githubusercontent.com/google/fonts/main/ofl/instrumentserif/InstrumentSerif-Italic.ttf",
}


def get(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print("have", os.path.relpath(dest, HERE))
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print("get ", url)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


if __name__ == "__main__":
    for cid, (url, _) in CLIPS.items():
        get(url, os.path.join(ASSETS, "clips", f"{cid}.mp4"))
    for name, url in MUSIC.items():
        get(url, os.path.join(ASSETS, "music", name))
    for name, url in FONTS.items():
        get(url, os.path.join(ASSETS, "fonts", name))
