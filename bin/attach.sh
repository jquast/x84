#!/bin/ksh -x
# quickly attaches to bbs, executing if necessary
export BBSPATH=/bbs
DTACH="/usr/local/bin/dtach"
if [ -x $DTACH ]; then
	$DTACH -A $BBSPATH/bbs.sock $BBSPATH/startup.sh
else
	.$BBSPATH/startup.sh
fi
