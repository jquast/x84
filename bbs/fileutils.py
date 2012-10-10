"""
misc. file routine helpers for X/84 (formerly, 'The Progressive') BBS.
"""
import os

# file contents
#def read_gzip(filename):
#  " pass filepath of gzip, return uncompressed data"
#  try:
#    import gzip
#  except:
#    return ['cannot load module: gzip']
#  return gzip.GzipFile(filename, mode='rb').data()
#
#def read_bzip(filename):
#  " pass filepath of bzip, return uncompressed data"
#  try:
#    import bz2
#  except:
#    return ['cannot load module: bz2']
#  return bz2.BZ2File(filename, mode='rb').data()

#def list_zip(filename):
#  """ pass zipfile, return listing of zipfile contents """
#  try:
#    import zipfile
#  except:
#    return ['cannot load module: zipfile']
#  data = ''
#  data = ["%-49s %19s %7s" %
#    ("filename", "last modified", "size")]
#  zipdata = zipfile.ZipFile(filename, mode="r")
#
#  for zipinfo in zipdata.filelist:
#     date = "%d-%02d-%02d %02d:%02d:%02d" % zipinfo.date_time
#     data.append ("%-49s %s %7s" %
 #      (zipinfo.filename, date, bytesize(zipinfo.file_size)))
#  return data
#
#def list_tar(filename):
#  """ pass filename of tar file, return listing of tarfile contents """
#  import time
#  try:
#    import tarfile
#  except:
#    return ['cannot load module: tarfile']
#  data = ["%10s %5s %5s %5s %10s %8s %s" %
#    ('mode', 'uid', 'gid', 'size', 'date', 'time', 'filename')]
#  tardata = tarfile.open (filename, mode)
#
#  for tarinfo in tardata:
#    string = tarfile.filemode(tarinfo.mode) + " %4s%4s" % (tarinfo.uid, tarinfo.gid)
#    if tarinfo.ischr() or tarinfo.isblk():
#      string += " %8s" % ("%d,%d" % (tarinfo.devmajor, tarinfo.devminor))
#    else:
#      string += " %8s" % bytesize(tarinfo.size)
#    data.append (string + " %d-%02d-%02d %02d:%02d:%02d " %
#      time.localtime(tarinfo.mtime)[:6] + tarinfo.name)
#  return data
#
#def parentdir(path):
#  """
#  return parent directory of path by adding os-specific '../' to end of
#  path and returning the absolute directory
#  """
#  return os.path.abspath(os.path.join(path, os.path.pardir +os.path.sep))

def abspath(filename=None):
    """
    return absolute path under context of current session, including calls from
    bbs engine, where no session exists. With no arguments, the current working
    directory is returned
    """
    import session
    if (filename and not filename.startswith(os.path.sep)) or not filename:
        # find apropriate relative filepath
        try:
            # called from user session
            path = session.getsession().cwd
        except KeyError:
            # called from main engine daemon
            path = os.path.curdir
        if filename:
            path = os.path.join(path, filename)
    else:
        path = filename
    return os.path.normpath(path)

def fopen(filepath, mode='rb'):
    " return file descripter of file described by filepath, relative to session path "
    return open(abspath(filepath),mode)

def ropen(filename, mode='rb'):
    import glob
    " open random file, describing file listing using glob wildcards "
    import random
    return open(random.choice(glob.glob(abspath(filename))))
