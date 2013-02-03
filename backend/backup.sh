#!/bin/bash

cd /root/workspace/FantasyEmail/backend

pushd ..

mkdir -p archives
echo "*" > archives/.gitignore
tar cvfz archives/backup-$(date +"%s").tar.bz2 db /var/mail/itp ~itp/mbox



