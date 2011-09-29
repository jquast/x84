import imp,os,time,sys, logging

import fileutils

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
scriptpath=None

def scriptinit(sp):
  global scriptpath
  scriptpath = sp
  assert scriptpath is not None
  """
  Initialize the global scriptlist[], a cache store for run-time imports,
  reloading, dependencies, and sharing. By sharing scripts in this way,
  users may communicate across global variables, and share memory regions.
  It is recommended, however, to use the database subsystem to share large
  data segments, and the event subsystem to communicate across threads.
  """
  global scriptlist
  # Scripts and modules cache
  scriptlist = {}

  # load global bbs.py into scriptlist
  scriptimport ('bbs', False, *imp.find_module('bbs'))
  loadscript ('bbs')
  populatescript ('bbs')

def scriptimport(name, asDependancy, file, filename, desc=('.py','U',imp.PY_SOURCE)):
  """
  This function is a wrapper for imp.load_module. Arguments C{name}, C{file},
  C{filename}, and C{desc} is given information returned by find_module(), just
  as imp.load_module. See L{scriptinit} for an example.

  @param asDependancy: This argument, when True, signifies that this script
  import is a refresh of an existing script, that may be a dependancy (as specified
  by the C{deps[]} list of said script) to other scripts that may require their
  imported namespace of said script to be refreshed.

  @todo: need to cache deps[] variable if script is refreshed, before refresh,
  and if this list changes after refresh, re-populate script.
  """
  logger.debug ('importing %s', name)
  script = imp.load_module(name, file, filename, desc)
  script._name     = name
  script._filename = filename
  script._filedate = os.path.getmtime (filename)
  script._loadtime = time.time()
  scriptlist[name] = script

  if not asDependancy:
    return

  # if this script was previously loaded in memory, all other scripts
  # that refer to this as a dependency in deps[] needs to have this
  # script repopulated into its namespace

  # fresh up in-memory copy
  scriptlist[name] = script

  for tgtscript in [key for key in scriptlist.keys() if key != name]:
    # iterate each target script except for ourselves
    if isDependancyOf(tgtscript, name):
      logger.debug ('%s identified dependency: %s', name, tgtscript)
      populatescript(tgtscript, loadonly_dep=name)

def isDependancyOf(script, dep):
  """
  @param script: Script to check for dependencies.
  @param dep: Dependency to check for in Script.
  @returns: True if script lists dep as a dependency.
  """
  try:
    scriptdeps = getattr(scriptlist[script], 'deps')
  except AttributeError:
    # no dependencies
    return False

  for chkdep in scriptdeps:
    # retrieve normalized path of dependency
    _deppath = chkdep.replace('.', os.path.sep)
    chkdepname, _filepath = chkmodpath(chkdep, parent=os.path.dirname(_deppath))
    if dep == chkdepname:
      return True
  return False

def populatescript(name, loadonly_dep=None):
  """
  Ensure all globals are populated into the target script's global namespace.

  Load only the namespace of module defined as 'loadonly_dep' into target
  script 'name', when defined.

  Populate target script with all values and functions from bbs.py, except
  those that begin with C{'_'}.

  Then, retrieve script attribute C{deps}, of type list or tuple, and return
  immediately if not available. Otherwise, insert all globals from each
  dependency from the matching module defined by target scripts 'deps'
  variable.
  """
  global scriptlist

  if loadonly_dep:
    deps = [loadonly_dep]
  else:
    try:
      # retrieve from memory
      deps = getattr(scriptlist[name], 'deps')
    except AttributeError:
      # script is without dependencies
      return

  for depname in deps:
    try:
      depname, filepath = chkmodpath(depname, parent=os.path.dirname(name))
    except LookupError:
      logger.error ('Failed to locate dependency %s for parent=%s', depname, name)
      continue

    if depname == name: # avoid circular dependencies
      logger.error ('%s dependends on itself, ignoring', name)
      continue
    status = checkscript(depname)
    if status == -1:
      logger.error ('Failed to load dependency %s for parent=%s', depname, name)
      continue
    source = scriptlist[depname]
    # copy all attributes into another's
    # global space 'deps' and 'init'
    keys=[k for k in dir(scriptlist[depname]) \
          if not k.startswith('_') \
          and not k in ['deps','init']]
    target = scriptlist[name]
    for key in keys:
      setattr (target, key, getattr(source, key))

def chkmodpath(name, parent):
  """
  return tuple (modpath, filepath), for module named by 'name'.
  """

  cur = os.path.curdir
  if parent.startswith (cur):
    parent = parent[len(cur):]

  name = name.replace('.', os.path.sep)

  # absolute path
  if parent.startswith (os.path.sep):
    name_a = os.path.join(parent, name)
    path_a = name_a + '.py'
    if os.path.exists (path_a):
      return (name_a, path_a)

  # as-is (path/X.py)
  name_r = os.path.join(parent, name)
  path_r = name_r + '.py'

  if not os.path.exists(path_r):
    # script-path relative
    name_l = os.path.join(scriptpath, name)
    path_l = name_l + '.py'

    if not os.path.exists(path_l):
      # kernel-path relative (./path/name.py)
      name_g = os.path.join(os.path.join(os.path.curdir, parent), name)
      path_g = name + '.py'
      if not os.path.exists(path_g):
        logger.error (' chkmodpath(name=%s, parent=%s): filepath not found:',
          name, parent)
        logger.error (' script relative: %s', path_r)
        logger.error ('      scriptpath: %s', path_l)
        logger.error ('      kernelpath: %s', path_g)
        raise LookupError, 'filepath not found: "%s"' % name
      else:
        return name, path_g
    else:
      return name_l, path_l
  else:
    return name_r, path_r

def loadscript(name, asDependancy=False):
  """
  load script specified by module relative to script path, and populate
  its' global namespace with contents of modules defined in list 'deps'.
  If script contains init() function, also execute that.
  """
  global scriptlist

  sessionpath = fileutils.abspath ()
  name, path = chkmodpath(name, sessionpath)

  abs_dir = os.path.abspath(os.path.dirname(path))
  if not abs_dir in sys.path:
    logger.debug ('insert into sys.path: %s @0', abs_dir) 
    sys.path.insert (0, abs_dir)

#  try:
  scriptimport (name, asDependancy, *imp.find_module(name.split(os.path.sep)[-1]))
#  except ImportError:
#    import log
#    log.tb (*sys.exc_info())
#    logger.error ('Failed to import script: %s', name)
#    logger.error ('Filepath: %s', path)
#    return False

  # load in script dependencies, specified by global deps=['module.name']
  populatescript (name)

  init = None
  try:
    init = getattr(scriptlist[name],'init')
  except AttributeError: pass

  if init is not None:
    # Run init() function of script on import, if available
    logger.info ('exec %s.init()', name)
    init ()

  return True

def scriptlastmodified(name):
  path = name.replace('.', os.path.sep) + '.py'
  assert scriptpath is not None
  if not os.path.exists(path):
    path = os.path.join(scriptpath, path)
  try:
    return os.path.getmtime (path)
  except OSError, e:
    logger.error ('modtime failed for %s: %s', path, e)
    return 0

def chkglobals():
  """
  ensure 'bbs' module, which contains globals (and functions) shared by all bbs
  clients is loaded in memory. If the modified time of bbs.py is newer than
  import date, it is reloaded. If the reload fails, then the previous space
  is reverted as recovery. If it has not been yet loaded, and loading fails,
  then, and only then, is an exception raised.
  """

  assert scriptpath is not None
  if not 'bbs' in scriptlist:
    scriptinit (scriptpath)

  bbs_swap = scriptlist['bbs']

  lastmodified = scriptlastmodified('bbs')
  if lastmodified > scriptlist['bbs']._loadtime:
    logger.info ("reloading 'bbs' globals module, modified %s ago.",
      strutils.ascitime(time.time() -lastmodified),)
    try:
      scriptinit (scriptpath)
    except Exception, e:
      # exception raised because a failure occured loading the new bbs script
      logger.error ("reload of bbs.py failed: %s", e)
      logger.tb (*sys.exc_info())
      logger.info ('File: "./bbs.py"')
      logger.warn ('bbs.py reverting to previous state')
      scriptlist['bbs'] = bbs_swap
      return False
  return True

def checkscript(name, forcereload=False):
  """
  Firstly, check if bbs.py requires reload, and do so.
  Then, reload specified script into memory under any of the following
  conditions:
    - bbs.py has been reloaded.
    - file has been modified since last run.
    - any of its' dependencies require reload.
  Then, return a value signifying the status of the script checked:
    - return >0 if the above conditions applied and caused a reload,
      returning the number of modules and scripts reloaded.
    - return 0 when script did not require reloading.
    - return -1 when not sucessfully loaded.

  This function is recursive.
  """
  global scriptlist

  # number of scripts and dependencies reloaded (return value)
  loaded = 0

  if not chkglobals ():
    logger.warn ('checkscript(%s) failed chckglobals(), continuing', name)

  try:
    name, path = chkmodpath (name, fileutils.abspath())
  except LookupError:
    return -1 # errors already logged

  if not forcereload and scriptlist.has_key(name) \
  and hasattr(scriptlist[name],'deps'):
    for depname in getattr(scriptlist[name], 'deps'):
      if depname == name:
        # avoid circular recursion
        continue
      # force reload of this script if any dependencies required refresh
      if checkscript(depname) > 0:
        logger.debug ('set forcereload=True, dependency depname=%s refreshed', depname)
        forcereload = True
        loaded += 1

  if not forcereload and not scriptlist.has_key(name):
    logger.debug ('%s first load', name)
    forcereload = True

  asDependancy = False
  if not forcereload and scriptlastmodified(name) > scriptlist[name]._filedate:
    logger.debug ('script %s modified %s ago. refresh', name,
      strutils.asctime(time.time()-scriptlastmodified(name)))
    forcereload = True
    asDependancy = True

  if forcereload:
    if not loadscript (name, asDependancy):
      return -1
    loaded += 1

  return loaded
