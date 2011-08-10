#!/bin/sh -x
# test 6!!
cd /tmp
rm -rf bbs
cvs -d /var/cvs co bbs
tar -czvpf prsv-1984-$(date +%D| sed -e 's/\//./g').tgz bbs
