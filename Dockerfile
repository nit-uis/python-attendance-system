FROM python:3

ARG GIT_TAG="no git tag"

ENV GIT_TAG=${GIT_TAG}

ADD . .

RUN \
#apt-get -y update && \
#apt-get -y install cron && \
#apt-get clean && \
pip install --upgrade pip && \
pip install -r requirements.txt

ENTRYPOINT [ "python", "./main.py", "-e", "minerva" ]
