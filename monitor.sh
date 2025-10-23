#!/bin/bash

if ! pactl list short modules | grep -q module-null-sink; then
    curl -d "⚠️⚠️ module-null-sink not found, recreating" https://ntfy.somwaki.com/streamer
    pactl load-module module-null-sink sink_name=audio_mix
    docker compose -f /home/steven/Music/streams/ffmpeg ps
    curl -d "module-null-sink reloaded, containers restarted ✅" https://ntfy.somwaki.com/streamer
fi
 