#!/bin/ksh -x

BBS_ROOT=`dirname $0`; cd $BBS_ROOT; BBS_ROOT=`pwd`
PYTHON=$(which python) || PYTHON=
if [ X"$PYTHON" == X"" ]; then
	PYTHON=$(which python2.5) || PYTHON=
fi
if [ X"$PYTHON" == X"" ]; then
	PYTHON=$(which python2.6) || PYTHON=
fi
if [ X"$PYTHON" == X"" ]; then
	echo "Could not locate python in System PATH"
	exit 1
fi

VER=`$PYTHON -V 2>&1|awk -F'.' '{print substr($1,length($1)) "." $2}'`
PP=$BBS_ROOT/lib/python$VER/site-packages
if [ ! -d $PP ]; then
	echo "python version not supported, see doc/dependencies.txt"
fi
[ -z $PYTHONPATH ] && PYTHONPATH=$PP || PYTHONPATH=$PP:$PYTHONPATH
export PYTHONPATH

MAIN=$BBS_ROOT/main.py
PID=$BBS_ROOT/data/pid

start_daemon() {
	printf "Starting... "
	if [ -f $PID ]; then
		if ps -p `cat $PID` >/dev/null; then
			echo "BBS already running! (`cat $PID`)"
			exit 1
		else
			echo "stale pid (`cat $PID`); removing."
			rm $PID
		fi
	fi
	if [ ! -d $BBS_ROOT/logs ]; then
		mkdir -p $BBS_ROOT/logs
	fi
	$PYTHON $MAIN >$BBS_ROOT/logs/daemon.err 2>&1 &
	echo $! > $PID
	echo " (`cat $PID`) ok"
}

stop_daemon() {
	printf "Stopping... "
	if [ ! -f $PID ]; then
		echo "BBS not running."
		exit 0
	fi
	n=0
	while [ $n -lt 10 ]; do
		if ! ps -p $pid >/dev/null 2>&1; then
			break
		else
			sleep 1
		fi
		let n="$n+1"
	done
	echo "(`cat $PID`) ok"
	rm $PID
}


if [ ! -x $PYTHON ]; then
	if which python >/dev/null; then
		PYTHON=`which python`
	else
		if which python2.5 >/dev/null; then
			PYTHON=`which python2.5`
		else
			echo "python not found."
		fi
	fi
fi

if [ X"$1" == X"-d" ]; then
	if [ -z "$2" ] || [ "$2" == "start" ]; then
		start_daemon
	elif [ "$2" == "stop" ]; then
		stop_daemon
	fi
else
	$PYTHON $MAIN $*
	ret=$?
	exit $ret
fi
