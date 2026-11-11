# Life in weeks  (19.6 s, 1080x1920, 30 fps)

Hook "If you're 20, this is your whole life" -> 4,160-dot grid (1 dot = 1 week) fills with the
rest of your life (sleep / work+chores / screens) while a phone battery drains to 14 % and the
signal dies -> DROP: rapid-fire footage cut on the beat, battery recharges -> "Your life can't. Start living."

    python3 fetch_assets.py            # free-licence clips + font into ./assets
    #   put the music at assets/music/luminary.mp3 and the ElevenLabs lines in assets/vo11/
    python3 build.py                   # ../out/life_in_weeks.mp4  (+ _no_music.mp4)
    python3 build.py --audio-only      # re-mix sound without re-rendering the picture
    python3 build.py --stills 1,3.4    # PNG stills of the graphic intro

* `timeline.py` - all timing, locked to the track's beat grid (67.4 BPM, drop at 7.057 s), and the numbers
* `audio.py`    - synthesised sound design + voice-over processing + music ducking/mix
* `build.py`    - renderer (numpy/Pillow) + ffmpeg encode

Stats are rough (ages 0-80, screens = 4 h/day); the footnote in the video says so.
