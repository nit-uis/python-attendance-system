FROM python:3.8-slim-buster
ARG GIT_TAG="no git tag"
ENV GIT_TAG=${GIT_TAG}
COPY . .
RUN pip install -r requirements.txt
ENTRYPOINT [ "python", "./main.py", "-e", "minerva" ]
