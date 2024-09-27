#!/bin/bash

mkdir -p ~/.afl/upload/

cp ./dashboard2.html ~/.afl/upload/
cp ./index.html ~/.afl/upload/

cp ./timeline.js ~/.afl/upload/
cp ./timeline.html ~/.afl/upload/

cp -n ./config.json ~/.afl/watchdog-config.json

sudo cp -n afl-watchdog.service /etc/systemd/system/
