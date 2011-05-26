#!/bin/bash
apt-get update
apt-get install -y xvfb libgtk2.0-0 libasound2 build-essential python-dev libevent-dev mongodb git python-pip python-virtualenv virtualenvwrapper puf openbox libxslt1-dev libxml2-dev html2text poppler-utils ghostscript antiword catdoc libjpeg8-dev libwpd-tools

cd /opt
wget http://releases.mozilla.org/pub/mozilla.org/firefox/releases/4.0/linux-x86_64/en-US/firefox-4.0.tar.bz2 -O - | tar xvfj -
ln -s /opt/firefox/firefox /usr/bin/firefox

mkdir /tmp/tesseract
cd /tmp/tesseract
wget http://ppa.launchpad.net/alex-p/notesalexp/ubuntu/pool/main/t/tesseract/tesseract-ocr_3.0.0+svn581-1ppa1~maverick1_i386.deb
wget http://ppa.launchpad.net/alex-p/notesalexp/ubuntu/pool/main/t/tesseract/tesseract-ocr-eng_3.0.0+svn581-1ppa1~maverick1_all.deb
dpkg -i *.deb
cd
rm -rf /tmp/tesseract
apt-get install -f
if [ ! -f /usr/lib/liblept.so.0 ]; then
    ln -s /usr/lib/liblept.so.1 /usr/lib/liblept.so.0
fi
