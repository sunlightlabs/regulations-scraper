#!/bin/bash
apt-get update
apt-get install -y xvfb libgtk2.0-0 libasound2 build-essential python-dev libevent-dev mongodb git python-pip python-virtualenv virtualenvwrapper

cd /opt
wget http://releases.mozilla.org/pub/mozilla.org/firefox/releases/4.0/linux-x86_64/en-US/firefox-4.0.tar.bz2 -O - | tar xvfj -
ln -s /opt/firefox/firefox /usr/bin/firefox
