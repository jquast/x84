#!/bin/ksh
OUTPATH=/var/www/cvs/bbs
epydoc --debug -v -o $OUTPATH --name x84 --css white \
--url http://cvs.1984.ws/bbs /bbs
cd $OUTPATH/doc
cvs up -Pd
