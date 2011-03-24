#!/bin/bash

source /etc/bash_completion
if [ ! -d $HOME/.virtualenvs ]; then
    mkdir $HOME/.virtualenvs
fi
mkvirtualenv scraper
workon scraper

pip install -r ../requirements.txt
