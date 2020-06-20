#! /bin/bash

# This is useful for a local test endpoint to receive RTMP

while :
    do
        ffmpeg -hide_banner -f flv -listen 1 -i rtmp://localhost:1935/app/live -f null -
done