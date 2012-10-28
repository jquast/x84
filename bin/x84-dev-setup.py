"""
setup virtualenv for x/84,
for source developers only !
"""
import sys
import os
import virtualenv
import subprocess

def main():
    """
    1. setup a non-root virtualenv environment,
    2. pip install required modules _REQUIREMENTS,
    3. pip install -e (leave source in-place)
       `dirname $0`/.. as 'x84'
    3. create an 'x84' executable, which
       a. sources virtualenv's 'activate' script
       b. calls `dirname $0`/python -m x84

    Program Argument:
        Installation folder [fe. ./ENV]
    """
    if len(sys.argv) != 2:
        sys.stderr.write ('%s [virtualenv folder]\n' % (sys.argv[0],))
        return 1

    path_install = sys.argv[1]
    path_tgtbin = os.path.join(path_install, 'bin', 'x84')
    path_symlink = os.path.join(os.path.dirname(__file__), 'x84-dev')
    path_x84 = os.path.join(os.path.dirname(__file__), os.path.pardir)
    path_requirements = os.path.join(path_x84, 'requirements.txt')
    path_pip = os.path.join(path_install, 'bin', 'pip')

    # install all required modules,
    virtualenv.create_environment (path_install)
    for pkg in open(path_requirements):
        subprocess.call([path_pip, 'install', pkg])

    # install x84, but it symlinks to our source tree (-e)
    subprocess.call([path_pip, 'install', '-e', path_x84])

    # write out shell script that calls the virtualenv-python
    open(path_tgtbin, 'wb').write(
            "#!/bin/sh\n"
            ". `dirname $(readlink $0)`/activate\n"
            "python -m x84.engine $*\n")
    os.chmod(path_tgtbin, 0755)
    if os.path.exists(path_symlink) and os.path.islink(path_symlink):
        os.unlink (path_symlink)
    os.symlink(os.path.abspath(path_tgtbin), path_symlink)
    sys.stdout.write ('Installation complete, to launch x/84, run:\n\n')
    sys.stdout.write ('    %s\n\n' % (path_symlink,))

if __name__ == '__main__':
    main()
