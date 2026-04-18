#!/usr/bin/env bash
set -o errexit

apt-get update
apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1 libcairo2

pip install -r requirements.txt
