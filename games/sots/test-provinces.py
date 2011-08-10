#!/usr/bin/env python
# test all default provinces for integrity

from data_province import *

for pkey in defaultProvinces.keys():
  print pkey,
  # for each province
  for nkey in defaultProvinces[pkey]['neighbors']:
    # for each neighbor
    if not defaultProvinces.has_key(nkey):
      # we cannot find our neighbor
      print 'cannot find neighbor', nkey, 'for province', pkey
      continue
    if not pkey in defaultProvinces[nkey]['neighbors']:
      # we are not listed as a neighbor in our neighbor province
      print nkey, 'is neighbor of', pkey, \
            'but', pkey, 'is not a neighbor of', nkey
    if nkey == pkey:
      # we are listing ourselves as a neighbor?
      print pkey, 'is a neighbor of itself'
  print
