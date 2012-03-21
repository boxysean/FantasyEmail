#!/bin/bash

cd /root/workspace/riskyListy/backend

pushd ..
source ./bin/activate
popd

python CheckMail.py
python AddEmailers.py
python ComputeScores.py
python ComputeEmailerScores.py


