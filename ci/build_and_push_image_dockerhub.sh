#!/bin/bash

# login first: docker login -u dotsenergyframework

VERSION=0.0.9
REPOSITORY="dotsenergyframework/simulation-orchestrator"

docker build -t ${REPOSITORY}:${VERSION} ./..

docker push ${REPOSITORY}:${VERSION}
