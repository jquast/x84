#!/bin/ksh
# creates bbs, for use as root in rc.d scripts
BBSPATH=/bbs
DTACH="/usr/local/bin/dtach"
if [ -x $DTACH ] && [ X"$(id -u)" == X"0" ]; then
	$DTACH -n $BBSPATH/bbs.sock $BBSPATH/startup.sh >/dev/null 2>&1
	if [ $? -eq 1 ]; then
		$BBSPATH/destroy.sh
		rm -f $BBSPATH/bbs.sock
		$DTACH -n $BBSPATH/bbs.sock $BBSPATH/startup.sh >/dev/null 2>&1
		if [ $? -eq 1 ]; then
			echo " failed!"
		else
			sleep 1
			chmod 660 $BBSPATH/bbs.sock $BBSPATH/data/system* $BBSPATH/debug.log
		fi
	else
		sleep 1
		chmod 660 $BBSPATH/bbs.sock $BBSPATH/data/system*
	fi
elif [ X"$(id -u)" != X"0" ]; then
	echo "this script is for non-interactive use by root"
	echo "use attach.sh to start the bbs in interactive mode"
else
	echo -n "dtach not found!"
	$BBSPATH/startup.sh
fi
