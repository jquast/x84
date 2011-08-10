"""
File utilities for 'The Progressive' BBS.
(c) Copyright 2006, 2007 Jeffrey Quast.
$Id: fileutils.py,v 1.10 2008/06/08 22:17:15 dingo Exp $

These functions support pagers, filebrowsers, etc.
"""
from time import localtime
import os
import dircache
import random
import glob
import strutils

import engine
from session import session, user
import log

# file contents
def read_gzip(filename):
  " pass filepath of gzip, return uncompressed data"
  try:
    import gzip
  except:
    return ['cannot load module: gzip']
  return gzip.GzipFile(filename, mode='rb').data()

def read_bzip(filename):
  " pass filepath of bzip, return uncompressed data"
  try:
    import bz2
  except:
    return ['cannot load module: bz2']
  return bz2.BZ2File(filename, mode='rb').data()

def list_zip(filename):
  """ pass zipfile, return listing of zipfile contents """
  try:
    import zipfile
  except:
    return ['cannot load module: zipfile']
  data = ''
  data = ["%-49s %19s %7s" %
    ("filename", "last modified", "size")]
  zipdata = zipfile.ZipFile(filename, mode="r")

  for zipinfo in zipdata.filelist:
     date = "%d-%02d-%02d %02d:%02d:%02d" % zipinfo.date_time
     data.append ("%-49s %s %7s" %
       (zipinfo.filename, date, bytesize(zipinfo.file_size)))
  return data

def list_tar(filename):
  """ pass filename of tar file, return listing of tarfile contents """
  try:
    import tarfile
  except:
    return ['cannot load module: tarfile']
  data = ["%10s %5s %5s %5s %10s %8s %s" %
    ('mode', 'uid', 'gid', 'size', 'date', 'time', 'filename')]
  tardata = tarfile.open (filename, mode)

  for tarinfo in tardata:
    string = tarfile.filemode(tarinfo.mode) + " %4s%4s" % (tarinfo.uid, tarinfo.gid)
    if tarinfo.ischr() or tarinfo.isblk():
      string += " %8s" % ("%d,%d" % (tarinfo.devmajor, tarinfo.devminor))
    else:
      string += " %8s" % bytesize(tarinfo.size)
    data.append (string + " %d-%02d-%02d %02d:%02d:%02d " %
      time.localtime(tarinfo.mtime)[:6] + tarinfo.name)
  return data

def listdir(dir, cache=True, sorted=False):
  " retrieve directory concents using dircache "
  if cache:
    list = dircache.listdir(dir)
  else:
    list = os.listdir(dir)
  if sorted:
    list.sort()
  return list

def getfiles(dir, cache=True, sorted=True):
  " Retrieve sorted file listing of current directory, akin to ls -F, "
  " except that directories are placed at front of list "
  list = []
  for entry in listdir(dir, cache, sorted):
    if os.path.isdir(os.path.join(dir, entry)): list.append (entry + os.path.sep)
  for entry in listdir(dir, cache, sorted):
    if os.path.isfile(os.path.join(dir, entry)): list.append (entry)
  return list

def parentdir(path):
  " return parent directory of path by adding os-specific '../' to end of "
  " path and returning the absolute directory "
  return os.path.abspath(os.path.join(path, os.path.pardir +os.path.sep))

def changedir(curpath, relpath):
  "   Pass current path and relative path, and return 'left' if "
  "   relative path brings us up one level, and 'right' if relative "
  "   path brings us further down a directory hierarchy. return "
  "   'action' if acting on a file, and 'failure' otherwise. "
  newpath = os.path.abspath(os.path.join(curpath, relpath))
  if newpath == parentdir(newpath):
    # traverse left
    return 'left', newpath
  elif os.path.isdir(newpath):
    # traverse right
    return 'right', newpath
  elif os.path.isfile(newpath):
    # take action on file
    return 'action', newpath
  else:
    # error
    log.write ('uncomparable paths, newpath='+str(newpath)+' from curpath='+curpath)


def abspath(filename=None):
  """
  return absolute path under context of current session, including calls from
  bbs engine, where no session exists. With no arguments, the current working
  directory is returned
  """
  if (filename and not filename.startswith(os.path.sep)) or not filename:
    # find apropriate relative filepath
    try:
      # called from user session
      path = engine.getsession().path
    except KeyError:
      # called from main engine daemon
      path = os.path.curdir
    if not path.endswith(os.path.sep):      # XXX necessary?
      path += os.path.sep                   # XXX
    if filename:
      path = os.path.join(path, filename)
  else:
    path = filename
  return os.path.normpath(path)

def fopen(filepath, mode='rb'):
  " return file descripter of file described by filepath, relative to session path "
  return open(abspath(filepath),mode)

def ropen(filename, mode='rb'):
  " open random file, describing file listing using glob wildcards "
  return open(random.choice(glob.glob(abspath(filename))))

