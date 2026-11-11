# Life in weeks (27.7 s, 1080x1920, 30 fps)

Data-viz intro (4,160 dots = 80 years in weeks, drawn in code) -> drop -> stock footage
cut on the beat while a phone status bar loses signal and recharges.

    python3 fetch_assets.py   # downloads free-licence clips, music, font into ./assets
    python3 build.py          # renders ../out/life_in_weeks.mp4
    python3 build.py --stills 5,9.6   # PNG stills of the graphic intro

* `timeline.py` – all timing (locked to the track: 100 BPM, drop at 14.82 s) and the numbers
* `sfx.py` – synthesised sound design (ticks, riser, impact, whooshes, "full battery" bell)
* `build.py` – renderer + ffmpeg encode

Assets: Mixkit free video/music licence, Instrument Serif (SIL OFL). Stats are rough
estimates (ages 20-80, screens = 4 h/day) and the footnote in the video says so.
