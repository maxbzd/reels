# The breakup  (30 s, 1080x1920, 30 fps)

A chat between you and the personified Instagram app: "hey. you up?" ... "you can't block me." ->
finger taps Block -> "Instagram is blocked until 8:00" -> "Not delivered" -> "Comment BLOCK".
No footage: the whole phone UI (bubbles, typing dots, keyboard, alert, touch indicator) is drawn in code.

    python3 render.py                # ../out/breakup.mp4  +  breakup_no_music.mp4
    python3 render.py --audio-only   # re-mix sound only
    python3 render.py --stills 5,24.9

* `script.py` - the script (messages, timing, clock) - edit the text here
* `render.py` - picture; `sound.py` - synthesised chat sounds + music mix
* music: assets/music/time.mp3 (Hans Zimmer - Time, 30 s instrumental preview supplied by the author), kept very quiet;
  swap the file + edit `music_gain()` in sound.py to try another track.
