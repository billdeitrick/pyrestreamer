FROM python:3.8-slim-buster

WORKDIR /opt/app

COPY pyrestreamer pyrestreamer
COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
COPY run.sh run.sh
COPY run.py run.py

RUN apt-get update
RUN apt-get install -y wget
RUN apt-get install -y gnupg

# Using streamlink fork due to DASH manifest retry issue
#RUN wget -qO- "https://bintray.com/user/downloadSubjectPublicKey?username=amurzeau" | apt-key add -
#RUN echo "deb https://dl.bintray.com/amurzeau/streamlink-debian stretch-backports main" | tee "/etc/apt/sources.list.d/streamlink.list"

RUN apt-get update
RUN apt-get install -y ffmpeg

# Using streamlink fork due to DASH manifest retry issue
#RUN apt-get install -y streamlink

RUN pip install https://github.com/billdeitrick/streamlink/archive/dash-args.zip

RUN pip install pipenv
RUN mkdir .venv
RUN pipenv install

ENTRYPOINT ["./boot.sh"]
