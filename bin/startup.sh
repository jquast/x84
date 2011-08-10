#!/bin/ksh -x
PYTHON=/usr/local/bin/python
BBSPATH=/bbs
BBSUSER=bbs
BBSGROUP=bbs
cd $BBSPATH

[ X"$(id -u)" == X"0" ] && SUDO="" || SUDO="sudo"

$SUDO su $BBSUSER -c "$PYTHON $BBSPATH/main.py 2>$BBSPATH/stderr.log"
ret=$?
if [ $ret -ne 1 ]; then
	sleep 1
	$SUDO chmod 660 $BBSPATH/bbs.sock $BBSPATH/data/system*
	$SUDO chgrp $BBSGROUP $BBSPATH/data/system*
	$SUDO chgrp $BBSGROUP $BBSPATH/stderr.log $BBSPATH/debug.log
fi
exit $ret
