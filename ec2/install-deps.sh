#!/bin/bash
apt-get update
apt-get install -y build-essential python2.7-dev libevent-dev git python-pip python-virtualenv virtualenvwrapper puf openbox libxslt1-dev libxml2-dev html2text poppler-utils ghostscript antiword catdoc libjpeg8-dev libwpd-tools

mkdir /tmp/tesseract
cd /tmp/tesseract
wget http://ppa.launchpad.net/alex-p/notesalexp/ubuntu/pool/main/t/tesseract/tesseract-ocr_3.0.0+svn590-2ppa1~maverick1_amd64.deb
wget http://ppa.launchpad.net/alex-p/notesalexp/ubuntu/pool/main/t/tesseract/tesseract-ocr-eng_3.0.0+svn590-2ppa1~maverick1_all.deb
dpkg -i *.deb
cd
rm -rf /tmp/tesseract
apt-get install -f
if [ ! -f /usr/lib/liblept.so.0 ]; then
    ln -s /usr/lib/liblept.so.1 /usr/lib/liblept.so.0
fi
