# Put this and 'second.py' directly in your cfg.scriptpath and change 
# the strings here, in second.py and the depstest function in bbs.py
# to test and verify that script reloading works.

deps = [ 'second' ]

def main():
  echo ('Hello brave new world.. or ?!')
  echo ('second says: ' + hello() )
  readkey()
