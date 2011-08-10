#!/bin/ksh
[ X"$(id -u)" == X"0" ] && SUDO="" || SUDO="sudo"
for pid in $(pgrep -u bbs); do
	ps $pid 2>/dev/null
	$SUDO kill $pid 2>/dev/null
	$SUDO kill -9 $pid 2>/dev/null
done
