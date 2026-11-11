# The breakup  (30 s, 1080x1920, 30 fps)

A chat between you and the personified Instagram app: "hey. you up?" ... "you can't block me." ->
finger taps Block -> "Instagram is blocked until 8:00" -> "Not delivered" -> "Comment BLOCK".
No footage: the whole phone UI (bubbles, typing dots, keyboard, alert, touch indicator) is drawn in code.

    python3 render.py                # ../out/breakup.mp4  +  breakup_no_music.mp4
    python3 render.py --audio-only   # re-mix sound only
    python3 render.py --stills 5,24.9

* `script.py` - the script (messages, timing, clock) - edit the text here
* `render.py` - picture; `sound.py` - synthesised chat sounds + music mix
* music: assets/music/luminary.mp3 (Joel Sunny - Luminary, supplied by the author). Its swell lands on
  "47 min later" (7.06 s) and its biggest hit on the Block tap (24.86 s).
