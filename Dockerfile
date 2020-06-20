FROM python:3.8-slim-buster

WORKDIR /opt/app

COPY pyrestreamer pyrestreamer
COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
COPY run.py run.py

RUN apt-get update
RUN apt-get install -y wget
RUN apt-get install -y gnupg

RUN wget -qO- "https://bintray.com/user/downloadSubjectPublicKey?username=amurzeau" | apt-key add -
RUN echo "deb https://dl.bintray.com/amurzeau/streamlink-debian stretch-backports main" | tee "/etc/apt/sources.list.d/streamlink.list"

RUN apt-get update
RUN apt-get install -y ffmpeg
RUN apt-get install -y streamlink

RUN pip install pipenv
RUN mkdir .venv
RUN pipenv install

ENTRYPOINT ["/opt/app/.venv/bin/python", "-u", "run.py"]
