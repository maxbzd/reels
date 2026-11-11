# The breakup - film version (~39 s, 1080x1920, 30 fps)

Real footage of a man lying on a bed scrolling Reels -> the camera flies into the phone when the message
arrives -> the chat reel (`../breakup`) plays on the full-screen phone UI.

    python3 feedui.py            # builds the Reels UI overlay + the swiping feed (needs assets/clips/*.mp4)
    ffmpeg -i assets/ui/feed.mp4 -t 10.2 -qscale:v 2 assets/ui/feed/%04d.jpg
    python3 film.py              # ../out/breakup_film.mp4 (+ _no_music)
    python3 film.py --stills 3,8 # stills

* `comp.py`   - virtual camera, perspective-mapping of our UI onto the real phone screen, finger occlusion,
                grade / vignette / grain
* `feedui.py` - the Reels feed shown on his phone;  `film.py` - timeline;  `audio_film.py` - sound
* Footage (Mixkit free licence): "A man lying on the bed scrolling on his phone" (wide) and
  "A man lying on the bed scrolling food pictures on his phone" (close-up).  The screen corners were
  keyframed by hand (`Q62`, `Q164` in film.py); the original food app on his screen is fully replaced.
