# PyReStreamer

PyRestreamer is a simple app built with [FFMPEG](https://ffmpeg.org/), [Streamlink](https://streamlink.github.io/), [Docker](https://www.docker.com/), and [Python](https://www.python.org/) to re-stream video content from DASH or HLS streams to RTMP. One possible use case is to allow re-broadcasting content from sources that only provide DASH or HLS endpoints to other services and endpoints that require RTMP.

The general idea is that you specify the times you would like to be actively re-streaming, and then PyReStreamer will automatically start streaming at the specified time and stop after the specified duration. FFMPEG is used under the hood, so you can output anything supported by FFMPEG.

This app was specifically built to automate restreaming from [Living as One](https://livingasone.com/) to [PhoneLiveStreaming.com](https://phonelivestreaming.com/).

## Setting Up PyReStreamer

PyReStreamer is designed to be deployed in a Docker container. As such, you'll need a host running Docker Engine to get started. Once you've got that up and running, these steps will get you started:

1. Pull the image from Docker Hub: `docker pull billdeitrick/pyrestreamer`
1. Copy the sample .env and logging.yml files to your Docker host. I generally put them in `/opt/pyrestreamer`.
1. Copy the sample [.env](https://github.com/billdeitrick/pyrestreamer/blob/master/sample.env) and [logging.yml](https://github.com/billdeitrick/pyrestreamer/blob/master/logging-sample.yml) files and edit according to your requirements. The .env file is fairly well documented, and the logging.yml file is configured for suitable Docker defaults. [PushOver](https://pushover.net/) support is built in (in example file) if you are a PushOver user. Otherwise, you can learn more about logging options in the Python [docs](https://docs.python.org/3/howto/logging.html).
1. Start the container; here's an example command:

```bash
docker run --name pyrestreamer --restart unless-stopped --env-file /path/to/.env -v /path/to/logging.yml:/opt/app/logging.yml billdeitrick/pyrestreamer
```