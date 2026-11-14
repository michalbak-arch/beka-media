#!/bin/bash
# usage: mix.sh video_noaudio.mp4 lektor.mp3 muzyka.mp3 out.mp4
set -e
V=$1; VO=$2; MU=$3; OUT=$4
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")
ffmpeg -y -loglevel error -i "$V" -i "$VO" -i "$MU" -filter_complex "\
[1:a]aresample=48000,adelay=0|0,loudnorm=I=-15:TP=-1.5:LRA=9,asplit=2[vo][sc];\
[2:a]aresample=48000,volume=0.55,afade=t=out:st=$(python3 -c "print($D-1.8)"):d=1.8[mu];\
[sc]apad=whole_dur=90[scp];[mu][scp]sidechaincompress=threshold=0.04:ratio=8:attack=20:release=350[duck];\
[vo][duck]amix=inputs=2:duration=longest:normalize=0,apad,atrim=0:$D[a]" \
-map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest "$OUT"
echo mixed $OUT
