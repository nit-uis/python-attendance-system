#!/bin/bash

function push() {
    # fixme fail for python 3.8
    #pip-compile requirements.in > requirements.txt
    GIT_TAG=$(git log -n 1 --pretty=format:%h)
    STATUS=$?
    if [[ ${STATUS} -ne 0 ]]
    then
      echo "--- ERROR"
      exit 1
    fi

    docker build --build-arg GIT_TAG="${GIT_TAG}" -t nituis/pas-minerva:latest .
    docker push nituis/pas-minerva:latest
    #git push
}

function pull() {
    docker pull nituis/pas-minerva:latest
    docker stop pas-minerva
    docker rm pas-minerva
    docker run -d -e minerva --name pas-minerva nituis/pas-minerva:latest
    docker logs -f pas-minerva
}

function test() {
#    deactivate
    pip-compile requirements.in > requirements.txt
    GIT_TAG=$(git log -n 1 --pretty=format:%h)
    docker build --no-cache --build-arg GIT_TAG="${GIT_TAG}" -t nituis/pas-minerva:latest .
    docker stop pas-minerva
    docker rm pas-minerva
    docker run -e "ENV=local"  --name pas-minerva nituis/pas-minerva:latest
}

function startNeo4j() {
    echo "restarting Neo4j..."
    docker stop minerva-neo4j
    docker rm minerva-neo4j
    docker run -d  --name=minerva-neo4j -p 7472:7474 -p 7682:7687  -v $HOME/minerva-neo4j/data:/var/lib/neo4j/data -v $HOME/minerva-neo4j/logs:/var/lib/neo4j/logs -v $HOME/minerva-neo4j/import:/var/lib/neo4j/import neo4j:latest
}

case "$1" in
  push)
    push
    ;;
  pull)
    pull
    ;;
  test)
    test
    ;;
  startNeo4j)
    startNeo4j
    ;;
  *)
    echo "Usage: [push|pull|test|startNeo4j]"
    ;;
esac