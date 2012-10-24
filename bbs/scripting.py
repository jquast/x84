"""
Scripting package for x/84, http://github.com/jquast/x84/
"""
import os
import io
import imp
import logging

SCRIPT_PATH = 'default/'
#pylint: disable=C0103
#        Invalid name "logger" for type constant (should match
logger = logging.getLogger()

def init(global_script_path):
    """
    Set the folder path where all scripts referenced as parameters to
    session goto() and gosub() calls are found.
    """
    #pylint: disable=W0603
    #        Using the global statement
    global SCRIPT_PATH
    SCRIPT_PATH = global_script_path

def chkmodpath(name, parent):
    """
    return tuple (modpath, filepath), for module named by 'name'.
    """

    cur = os.path.curdir
    if parent.startswith (cur):
        logger.debug ('Trimming %s from %s', os.path.curdir, cur)
        parent = parent[len(cur):]

    # absolute path
    if parent.startswith (os.path.sep):
        name_a = os.path.join(parent, name)
        path_a = name_a + '.py'
        if os.path.exists (path_a):
            #logger.debug ('absolute path match: (%s, %s)', name_a, path_a)
            return (name_a, path_a)

    # as-is (path/X.py)
    name_r = os.path.join(parent, name)
    path_r = name_r + '.py'
    if os.path.exists(path_r):
        logger.debug ('relative path match: (%s, %s)', name_r, path_r)
        return name_r, path_r

    # script-path relative
    name_l = os.path.join(SCRIPT_PATH, name)
    path_l = name_l + '.py'
    if os.path.exists(path_l):
        logger.debug ('script-path match: (%s, %s)', name_l, path_l)
        return name_l, path_l

    # kernel-path relative (./path/name.py)
    #name_g = os.path.join(os.path.join(os.path.curdir, parent), name)
    path_g = name + '.py'
    if os.path.exists(path_g):
        logger.debug ('kern-path match: (%s, %s)', name, path_g)
        return name, path_g

    raise LookupError, \
        'filepath not found: "%s" (parent=%s), tried: %s' \
        % (name, parent, ', '.join(set((path_r, path_l, path_g,))),)

def load(cwd, script_name):
    """
    import and return script specified by module-like name.
    The 'current working directory' of the script should also
    be specified as cwd, and should be in sys.path.
    """
    #pylint: disable=W0612
    #        Unused variable 'module_path'
    module_name, module_path = chkmodpath(script_name, cwd)
    return imp.load_module (module_name,
        *imp.find_module(os.path.split(module_name)[-1]))

def abspath(filename=None):
    """
    Return absolute path under context of current os.path.curdir
    """
    # deprecate ?
    if (filename and not filename.startswith(os.path.sep)) or not filename:
        # find apropriate relative filepath
        path = os.path.curdir
        if filename:
            path = os.path.join(path, filename)
    else:
        path = filename
    return os.path.normpath(path)

def fopen(filepath, mode='rb'):
    """
    Return wrap to io.open using script-relative filepath and mode of 'rb'.
    """
    return open(abspath(filepath), mode)

def ropen(filename, mode='rb'):
    """
    Open random file using wildcard (glob)
    """
    import glob
    import random
    return open(random.choice(glob.glob(abspath(filename))), mode)
