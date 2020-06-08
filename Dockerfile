FROM python:3.8-slim-buster

ARG GIT_TAG="no git tag"
ENV GIT_TAG=${GIT_TAG}
COPY requirements.txt requirements.txt
ADD . .
RUN apt-get -y update && \
apt-get -y upgrade && \
apt-get -y install curl && \
apt-get clean && \
pip install --upgrade pip && \
pip install -r requirements.txt

ENTRYPOINT [ "python", "./main.py", "-e", "minerva" ]
