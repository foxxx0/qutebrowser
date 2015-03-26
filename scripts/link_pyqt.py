#!/usr/bin/env python3
# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014-2015 Florian Bruhin (The Compiler) <mail@qutebrowser.org>

# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Symlink PyQt into a given virtualenv."""

import os
import argparse
import shutil
import os.path
import sys
import glob
import subprocess


class Error(Exception):

    """Exception raised when linking fails."""

    pass


def verbose_copy(src, dst, *, follow_symlinks=True):
    """Copy function for shutil.copytree which prints copied files."""
    print('{} -> {}'.format(src, dst))
    shutil.copy(src, dst, follow_symlinks=follow_symlinks)


def get_ignored_files(directory, files):
    """Get the files which should be ignored for link_pyqt() on Windows."""
    needed_exts = ('.py', '.dll', '.pyd', '.so')
    ignored_dirs = ('examples', 'qml', 'uic', 'doc')
    filtered = []
    for f in files:
        ext = os.path.splitext(f)[1]
        full_path = os.path.join(directory, f)
        if os.path.isdir(full_path) and f in ignored_dirs:
            filtered.append(f)
        elif (ext not in needed_exts) and os.path.isfile(full_path):
            filtered.append(f)
    return filtered


def link_pyqt(sys_path, venv_path):
    """Symlink the systemwide PyQt/sip into the venv.

    Args:
        sys_path: The path to the system-wide site-packages.
        venv_path: The path to the virtualenv site-packages.
    """
    globbed_sip = (glob.glob(os.path.join(sys_path, 'sip*.so')) +
                   glob.glob(os.path.join(sys_path, 'sip*.pyd')))
    if not globbed_sip:
        raise Error("Did not find sip in {}!".format(sys_path))

    files = ['PyQt5']
    files += [os.path.basename(e) for e in globbed_sip]
    for fn in files:
        source = os.path.join(sys_path, fn)
        dest = os.path.join(venv_path, fn)
        if not os.path.exists(source):
            raise FileNotFoundError(source)
        if os.path.exists(dest):
            if os.path.isdir(dest) and not os.path.islink(dest):
                shutil.rmtree(dest)
            else:
                os.unlink(dest)
        if os.name == 'nt':
            if os.path.isdir(source):
                shutil.copytree(source, dest, ignore=get_ignored_files,
                                copy_function=verbose_copy)
            else:
                print('{} -> {}'.format(source, dest))
                shutil.copy(source, dest)
        else:
            print('{} -> {}'.format(source, dest))
            os.symlink(source, dest)


def get_python_lib(executable):
    """Get the python site-packages directory for the given executable."""
    return subprocess.check_output(
        [executable, '-c', 'from distutils.sysconfig import get_python_lib\n'
         'print(get_python_lib())'], universal_newlines=True).rstrip()


def get_tox_syspython(venv_path):
    """Get the system python based on a virtualenv created by tox."""
    path = os.path.join(venv_path, '.tox-config1')
    with open(path, encoding='ascii') as f:
        line = f.readline()
    _md5, sys_python = line.rstrip().split(' ')
    return sys_python


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help="Base path to the venv.")
    parser.add_argument('site_path', help="Path to the venv site-packages "
                        "folder (for tox).", nargs='?')
    parser.add_argument('--tox', help="Add when called via tox.",
                        action='store_true')
    args = parser.parse_args()

    if args.tox:
        sys_path = get_python_lib(get_tox_syspython(args.path))
    else:
        sys_path = get_python_lib(sys.executable)

    if args.site_path is None:
        subdir = 'Scripts' if os.name == 'nt' else 'bin'
        executable = os.path.join(args.path, subdir, 'python')
        venv_path = get_python_lib(executable)
    else:
        venv_path = args.site_path

    link_pyqt(sys_path, venv_path)


if __name__ == '__main__':
    try:
        main()
    except Error as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
