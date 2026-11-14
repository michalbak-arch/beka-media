#!/bin/bash
# usage: render_all.sh timing.json out_noaudio.mp4
set -e
cd /home/claude/reel
T=$1; OUT=$2
python3 render.py $T part0.mp4 --part 0/2 > log0.txt 2>&1 &
python3 render.py $T part1.mp4 --part 1/2 > log1.txt 2>&1 &
wait
printf "file 'part0.mp4'\nfile 'part1.mp4'\n" > parts.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i parts.txt -c copy $OUT
echo rendered $OUT
