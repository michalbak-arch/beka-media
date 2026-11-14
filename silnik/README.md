# Silnik rolek — Beka z Przedsiębiorczości / Founders

Animacje rysowane w kodzie (Python + PIL + ffmpeg), 1080×1920, 30 fps.

- `chars.py` — postacie i rekwizyty (Chipek, sylwetki, gazety, bilet, Kapitol…), fonty z polskimi znakami
- `rolki/<data>-<temat>/render.py` — sceny konkretnej rolki (PLAN = lista scen przypiętych do akapitów lektora)
- `transcribe.py` — znaczniki czasu słów z lektora (faster-whisper small, model z npm `@skillninja/shortmovie-telop-model-p0..p3`)
- `align_asr.py` — dopasowanie słów scenariusza do czasów z Whispera → `timing.json`
- `render_all.sh timing.json out.mp4` — render równoległy (2 procesy)
- `mix.sh video.mp4 lektor.mp3 muzyka.mp3 out.mp4` — lektor znormalizowany, muzyka ściszana pod głosem (sidechain), wyciszenie na końcu

Lektor i muzyka: ElevenLabs (eleven_v4, tagi emocji w nawiasach kwadratowych). Gotowe rolki: katalog `rolki/` w głównym folderze repozytorium (publiczne linki dla Metricoola).
