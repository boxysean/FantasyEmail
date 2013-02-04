#!/bin/bash

cd `dirname "$0"`
source ./bin/activate

python manage.py CheckMail
python manage.py ComputeScores
python manage.py ComputeEmailerScores

